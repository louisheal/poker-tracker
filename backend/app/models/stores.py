from __future__ import annotations

from datetime import date

from .events import FlopEvent, LineEvent, TurnEvent, RiverEvent
from .filters import FlopFilter, LineFilter, TurnFilter, RiverFilter
from .enums import ActionSequence, MadeHandType, DrawType


def _in_date_range(played_on: date, start: date | None, end: date | None) -> bool:
	if start and played_on < start:
		return False
	if end and played_on > end:
		return False
	return True


class Flops:

	def __init__(self):
		self.events: list[FlopEvent] = []

	def add_event(self, event: FlopEvent):
		self.events.append(event)

	def json(self, filters: FlopFilter, start: date | None = None, end: date | None = None):
		n = 0
		cbet_count = 0
		fold_to_cbet = 0
		raise_to_cbet = 0
		donk_count = 0
		fold_to_donk = 0
		raise_to_donk = 0

		for e in self.events:
			if not _in_date_range(e.played_on, start, end):
				continue
			if not e.filter(filters):
				continue
			n += 1
			if e.cbet:
				cbet_count += 1
				if e.fold_to_cbet:
					fold_to_cbet += 1
				if e.raise_to_cbet:
					raise_to_cbet += 1
			if e.donk_bet:
				donk_count += 1
				if e.fold_to_donk_bet:
					fold_to_donk += 1
				if e.raise_to_donk_bet:
					raise_to_donk += 1

		if not n:
			return {"cbet_pct": 0, "fcbet_pct": 0, "raise_to_cbet_pct": 0, "donk_bet_pct": 0, "fold_to_donk_pct": 0, "raise_to_donk_pct": 0, "hand_count": 0}

		return {
			"cbet_pct": (cbet_count / n) * 100,
			"fcbet_pct": (fold_to_cbet / cbet_count * 100) if cbet_count else 0,
			"raise_to_cbet_pct": (raise_to_cbet / cbet_count * 100) if cbet_count else 0,
			"donk_bet_pct": (donk_count / n) * 100,
			"fold_to_donk_pct": (fold_to_donk / donk_count * 100) if donk_count else 0,
			"raise_to_donk_pct": (raise_to_donk / donk_count * 100) if donk_count else 0,
			"hand_count": n,
		}

	def bet_sizes(self, filters: FlopFilter, start: date | None = None, end: date | None = None):
		"""Return villain cbet sizes as list of pot-% values for distribution charting."""
		no_size_filter = FlopFilter(
			pot_types=filters.pot_types,
			board_types=filters.board_types,
			hero_preflop_raiser=filters.hero_preflop_raiser,
			hero_in_position=filters.hero_in_position,
			include_pool=filters.include_pool,
		)
		sizes = []
		for e in self.events:
			if not _in_date_range(e.played_on, start, end):
				continue
			if not e.filter(no_size_filter):
				continue
			if not e.hero_preflop_raiser and e.cbet_size_pct is not None:
				sizes.append(round(e.cbet_size_pct, 1))
		return sizes


class LineEvents:

	def __init__(self):
		self.events: list[LineEvent] = []

	def ev_node_data(
		self,
		f: LineFilter,
		flop_actions: list[str] | None,
		turn_actions: list[str] | None,
		river_actions: list[str] | None,
		start: date | None = None,
		end: date | None = None,
	) -> dict:
		from app.parsers.hand_types import classify_made_hand, classify_flush_draw, classify_straight_draw
		from app.parsers.equity import get_equity, VALID_TRIPLES

		# 1. Filter events + apply action prefixes
		events = [e for e in self.events if _in_date_range(e.played_on, start, end) and e.filter(f)]
		if flop_actions:
			events = self._filter_by_street_prefix(events, "flop", flop_actions)
		on_turn: bool = turn_actions is not None
		if on_turn:
			events = [e for e in events if e.turn_actions]
			if turn_actions:
				events = self._filter_by_street_prefix(events, "turn", turn_actions)
		on_river: bool = river_actions is not None
		if on_river:
			events = [e for e in events if e.river_actions]
			if river_actions:
				events = self._filter_by_street_prefix(events, "river", river_actions)

		POT_ATTR = {"river": "pot_at_river_bb", "turn": "pot_at_turn_bb", "flop": "pot_at_flop_bb"}

		if on_river:
			street = "river"
			depth = len(river_actions) if river_actions else 0
			actions_attr = "river_actions"
		elif on_turn:
			street = "turn"
			depth = len(turn_actions) if turn_actions else 0
			actions_attr = "turn_actions"
		else:
			street = "flop"
			depth = len(flop_actions) if flop_actions else 0
			actions_attr = "flop_actions"

		pot_attr = POT_ATTR[street]

		# 2. Determine who acts at this node
		next_actor: str | None = None
		for e in events:
			actions = getattr(e, actions_attr)
			if depth < len(actions):
				next_actor = actions[depth].actor
				break

		if next_actor is None:
			DEFAULT_EQUITY = 0.5
			pot_bb: float = sum(getattr(e, pot_attr, 0) for e in events) / len(events) if events else 0
			return {
				"equity_vs_full": {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
				"equity_vs_call": {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
				"equity_vs_raise": {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
				"fold_count": 0, "call_count": 0, "raise_count": 0,
				"median_raise_size_pct": None,
				"pot_bb": pot_bb, "street": street,
				"hand_count": len(events), "next_actor": None,
				"hero_faces_bet": False, "villain_bet_bb": None,
			}

		# 3. Init running sums
		full_eq_sum: dict[tuple, float] = {t: 0.0 for t in VALID_TRIPLES}
		call_eq_sum: dict[tuple, float] = {t: 0.0 for t in VALID_TRIPLES}
		raise_eq_sum: dict[tuple, float] = {t: 0.0 for t in VALID_TRIPLES}
		full_count: int = 0
		call_shown_count: int = 0
		raise_shown_count: int = 0

		fold_count: int = 0
		call_count: int = 0
		raise_count: int = 0
		raise_sizes: list[float] = []
		pot_sum: float = 0.0

		# hero_faces_bet detection
		hero_faces_bet: bool = False
		villain_bet_size_pct: float | None = None
		check_faces_bet = next_actor == "hero" and depth > 0

		# 4. Single pass
		for e in events:
			pot_sum += getattr(e, pot_attr, 0)

			actions = getattr(e, actions_attr)
			if depth >= len(actions):
				continue

			if check_faces_bet and villain_bet_size_pct is None:
				prev_action = actions[depth - 1]
				if prev_action.actor == "villain" and prev_action.action in ("B", "R") and prev_action.size_pct is not None:
					hero_faces_bet = True
					villain_bet_size_pct = prev_action.size_pct

			v_triple = None
			if e.villain_hand:
				board = self._build_board(e, on_turn, on_river)
				v_triple = (
					classify_made_hand(e.villain_hand, board),
					classify_flush_draw(e.villain_hand, board),
					classify_straight_draw(e.villain_hand, board),
				)
				full_count += 1
				for hero in VALID_TRIPLES:
					full_eq_sum[hero] += get_equity(hero, v_triple, street)

			hero_action = actions[depth]
			if hero_action.action not in ("B", "R"):
				continue

			reaction = None
			for idx in range(depth + 1, len(actions)):
				if actions[idx].actor == "villain":
					reaction = actions[idx]
					break

			if reaction is None:
				if len(actions) > depth + 1:
					fold_count += 1
				continue

			if reaction.action == "F":
				fold_count += 1
			elif reaction.action in ("C", "X"):
				call_count += 1
			elif reaction.action in ("R", "B"):
				raise_count += 1
				if reaction.size_pct is not None:
					raise_sizes.append(reaction.size_pct)

			if v_triple is not None:
				if reaction.action in ("C", "X"):
					call_shown_count += 1
					for hero in VALID_TRIPLES:
						call_eq_sum[hero] += get_equity(hero, v_triple, street)
				elif reaction.action in ("R", "B"):
					raise_shown_count += 1
					for hero in VALID_TRIPLES:
						raise_eq_sum[hero] += get_equity(hero, v_triple, street)

		# 5. Compute averages
		DEFAULT_EQUITY = 0.5
		n = len(events)
		equity_vs_full = {t: (full_eq_sum[t] / full_count if full_count else DEFAULT_EQUITY) for t in VALID_TRIPLES}
		equity_vs_call = {t: (call_eq_sum[t] / call_shown_count if call_shown_count else DEFAULT_EQUITY) for t in VALID_TRIPLES}
		equity_vs_raise = {t: (raise_eq_sum[t] / raise_shown_count if raise_shown_count else DEFAULT_EQUITY) for t in VALID_TRIPLES}
		median_raise: float | None = sorted(raise_sizes)[len(raise_sizes) // 2] if raise_sizes else None
		pot_bb: float = pot_sum / n if n else 0
		villain_bet_bb: float | None = (villain_bet_size_pct / 100) * pot_bb if hero_faces_bet and villain_bet_size_pct is not None else None

		return {
			"equity_vs_full": equity_vs_full,
			"equity_vs_call": equity_vs_call,
			"equity_vs_raise": equity_vs_raise,
			"fold_count": fold_count,
			"call_count": call_count,
			"raise_count": raise_count,
			"median_raise_size_pct": median_raise,
			"pot_bb": pot_bb,
			"street": street,
			"hand_count": n,
			"next_actor": next_actor,
			"hero_faces_bet": hero_faces_bet,
			"villain_bet_bb": villain_bet_bb,
		}

	def _build_board(self, e: LineEvent, on_turn: bool, on_river: bool) -> list:
		from playing_cards_lib.core import Card
		board: list[Card] = list(e.flop_cards)
		if on_turn and e.turn_card:
			board.append(e.turn_card)
		if on_river and e.river_card:
			board.append(e.river_card)
		return board

	def add_event(self, event: LineEvent):
		self.events.append(event)

	def spot_stats(self, f: LineFilter, flop_actions: list[str] | None = None, turn_actions: list[str] | None = None, river_actions: list[str] | None = None, start: date | None = None, end: date | None = None):
		events = [e for e in self.events if _in_date_range(e.played_on, start, end) and e.filter(f)]

		if flop_actions:
			events = self._filter_by_street_prefix(events, "flop", flop_actions)

		on_turn = turn_actions is not None
		if on_turn:
			events = [e for e in events if e.turn_actions]
			if turn_actions:
				events = self._filter_by_street_prefix(events, "turn", turn_actions)

		on_river = river_actions is not None
		if on_river:
			events = [e for e in events if e.river_actions]
			if river_actions:
				events = self._filter_by_street_prefix(events, "river", river_actions)

		if on_river:
			street = "river"
		elif on_turn:
			street = "turn"
		else:
			street = "flop"

		if not events:
			empty_stats = {
				"river": self._empty_river_stats,
				"turn": self._empty_turn_stats,
				"flop": self._empty_flop_stats,
			}
			return {
				"hand_count": 0,
				"street": street,
				"street_stats": empty_stats[street](),
				"ev_stats": self._empty_ev_stats(),
				"bet_sizes": [],
				"next_actor": None,
				"action_depth": len(river_actions or turn_actions or flop_actions or []),
				"flop_complete": on_turn or on_river,
				"turn_available": False,
				"turn_complete": on_river,
				"river_available": False,
				"top_wins": [],
				"top_losses": [],
			}

		n = len(events)

		if on_river:
			depth = len(river_actions) if river_actions else 0
			street_stats = self._compute_river_stats(events)
			actions_attr = "river_actions"
		elif on_turn:
			depth = len(turn_actions) if turn_actions else 0
			street_stats = self._compute_turn_stats(events)
			actions_attr = "turn_actions"
		else:
			depth = len(flop_actions) if flop_actions else 0
			street_stats = self._compute_flop_stats(events)
			actions_attr = "flop_actions"

		next_actions = self._compute_next_actions(events, depth, actions_attr)

		# Single pass for: overall_ev, next_actor, bet_sizes, availability flags
		pnl_sum = 0.0
		next_actor = None
		bet_sizes = []
		has_turn = False
		has_river = False

		import heapq
		TOP_N = 5
		top_wins: list[tuple[float, int, LineEvent]] = []
		top_losses: list[tuple[float, int, LineEvent]] = []

		for i, e in enumerate(events):
			pnl_sum += e.hero_pnl_bb
			if not has_turn and e.turn_actions:
				has_turn = True
			if not has_river and e.river_actions:
				has_river = True

			actions = getattr(e, actions_attr)
			if depth < len(actions):
				if next_actor is None:
					next_actor = actions[depth].actor
				a = actions[depth]
				if a.action in ("B", "R") and a.size_pct is not None:
					bet_sizes.append(a.size_pct)

			# Track top wins (max-heap via nlargest) and top losses (min-heap via nsmallest)
			if len(top_wins) < TOP_N:
				heapq.heappush(top_wins, (e.hero_pnl_bb, i, e))
			elif e.hero_pnl_bb > top_wins[0][0]:
				heapq.heapreplace(top_wins, (e.hero_pnl_bb, i, e))

			if len(top_losses) < TOP_N:
				heapq.heappush(top_losses, (-e.hero_pnl_bb, i, e))
			elif -e.hero_pnl_bb > top_losses[0][0]:
				heapq.heapreplace(top_losses, (-e.hero_pnl_bb, i, e))

		overall_ev = pnl_sum / n
		flop_complete = not on_turn and not on_river and next_actions == [] and has_turn
		turn_complete = on_turn and not on_river and next_actions == [] and has_river

		top_wins_sorted = [self._build_hand_result(e) for _, _, e in sorted(top_wins, reverse=True)]
		top_losses_sorted = [self._build_hand_result(e) for _, _, e in sorted(top_losses, reverse=True)]

		return {
			"hand_count": n,
			"street": street,
			"street_stats": street_stats,
			"ev_stats": {
				"overall_ev": overall_ev,
				"next_actions": next_actions,
			},
			"bet_sizes": [round(s, 1) for s in bet_sizes],
			"next_actor": next_actor,
			"action_depth": depth,
			"flop_complete": flop_complete or on_turn or on_river,
			"turn_available": has_turn,
			"turn_complete": turn_complete or on_river,
			"river_available": has_river,
			"top_wins": top_wins_sorted,
			"top_losses": top_losses_sorted,
		}

	def _build_hand_result(self, e: LineEvent) -> dict:
		return {
			"pnl_bb": round(e.hero_pnl_bb, 2),
			"hero_hand": [e.hero_hand.fst_card.to_json(), e.hero_hand.snd_card.to_json()] if e.hero_hand else None,
			"villain_hand": [e.villain_hand.fst_card.to_json(), e.villain_hand.snd_card.to_json()] if e.villain_hand else None,
			"flop": [c.to_json() for c in e.flop_cards],
			"turn_card": e.turn_card.to_json() if e.turn_card else None,
			"river_card": e.river_card.to_json() if e.river_card else None,
		}

	def _filter_by_street_prefix(self, events: list[LineEvent], street: str, prefix: list[str]) -> list[LineEvent]:
		actions_attr = {"flop": "flop_actions", "turn": "turn_actions", "river": "river_actions"}[street]
		result = []
		for e in events:
			actions = getattr(e, actions_attr)
			if len(actions) < len(prefix):
				continue
			match = True
			for i, p in enumerate(prefix):
				a = actions[i]
				if p in ("X", "F", "C"):
					if a.action != p:
						match = False
						break
				elif p.startswith("B") or p.startswith("R"):
					expected_action = p[0]
					if a.action != expected_action:
						match = False
						break
					size_part = p[1:]
					if size_part and a.size_pct is not None:
						if size_part.endswith("+"):
							lo = float(size_part[:-1])
							if a.size_pct < lo:
								match = False
								break
						else:
							parts = size_part.split("-")
							if len(parts) == 2:
								lo, hi = float(parts[0]), float(parts[1])
								if not (lo <= a.size_pct < hi):
									match = False
									break
				else:
					match = False
					break
			if match:
				result.append(e)
		return result

	def _compute_flop_stats(self, events: list[LineEvent]) -> dict:
		n = len(events)
		cbet_n = 0
		fold_to_cbet = 0
		raise_to_cbet = 0
		fold_to_cbet_raise = 0
		donk_n = 0
		fold_to_donk = 0
		raise_to_donk = 0
		fold_to_donk_raise = 0

		for e in events:
			if e.cbet:
				cbet_n += 1
				if e.fold_to_cbet:
					fold_to_cbet += 1
				if e.raise_to_cbet:
					raise_to_cbet += 1
				if e.fold_to_cbet_raise:
					fold_to_cbet_raise += 1
			if e.donk_bet:
				donk_n += 1
				if e.fold_to_donk_bet:
					fold_to_donk += 1
				if e.raise_to_donk_bet:
					raise_to_donk += 1
				if e.fold_to_donk_raise:
					fold_to_donk_raise += 1

		return {
			"cbet_pct": (cbet_n / n * 100) if n else 0,
			"fold_to_cbet_pct": (fold_to_cbet / cbet_n * 100) if cbet_n else 0,
			"raise_to_cbet_pct": (raise_to_cbet / cbet_n * 100) if cbet_n else 0,
			"fold_to_cbet_raise_pct": (fold_to_cbet_raise / max(1, raise_to_cbet) * 100) if cbet_n else 0,
			"donk_bet_pct": (donk_n / n * 100) if n else 0,
			"fold_to_donk_pct": (fold_to_donk / donk_n * 100) if donk_n else 0,
			"raise_to_donk_pct": (raise_to_donk / donk_n * 100) if donk_n else 0,
			"fold_to_donk_raise_pct": (fold_to_donk_raise / max(1, raise_to_donk) * 100) if donk_n else 0,
		}

	def _compute_turn_stats(self, events: list[LineEvent]) -> dict:
		n = len(events)
		hero_bet_n = 0
		villain_fold_to_hero = 0
		villain_raise_to_hero = 0
		villain_bet_n = 0
		hero_fold_to_villain = 0
		hero_raise_to_villain = 0

		for e in events:
			if not e.turn_actions:
				continue
			hero_bet = False
			villain_bet = False
			hero_fold = False
			hero_raise = False
			villain_fold = False
			villain_raise = False
			for a in e.turn_actions:
				if a.actor == "hero" and a.action == "B":
					hero_bet = True
				elif a.actor == "villain" and a.action == "B":
					villain_bet = True
				elif a.actor == "hero" and a.action == "F":
					hero_fold = True
				elif a.actor == "hero" and a.action == "R":
					hero_raise = True
				elif a.actor == "villain" and a.action == "F":
					villain_fold = True
				elif a.actor == "villain" and a.action == "R":
					villain_raise = True
			if hero_bet:
				hero_bet_n += 1
				if villain_fold:
					villain_fold_to_hero += 1
				if villain_raise:
					villain_raise_to_hero += 1
			if villain_bet:
				villain_bet_n += 1
				if hero_fold:
					hero_fold_to_villain += 1
				if hero_raise:
					hero_raise_to_villain += 1

		return {
			"hero_bet_pct": (hero_bet_n / n * 100) if n else 0,
			"villain_fold_to_hero_bet_pct": (villain_fold_to_hero / hero_bet_n * 100) if hero_bet_n else 0,
			"villain_raise_to_hero_bet_pct": (villain_raise_to_hero / hero_bet_n * 100) if hero_bet_n else 0,
			"villain_bet_pct": (villain_bet_n / n * 100) if n else 0,
			"hero_fold_to_villain_bet_pct": (hero_fold_to_villain / villain_bet_n * 100) if villain_bet_n else 0,
			"hero_raise_to_villain_bet_pct": (hero_raise_to_villain / villain_bet_n * 100) if villain_bet_n else 0,
		}

	def _compute_river_stats(self, events: list[LineEvent]) -> dict:
		n = len(events)
		hero_bet_n = 0
		villain_fold_to_hero = 0
		villain_raise_to_hero = 0
		villain_bet_n = 0
		hero_fold_to_villain = 0
		hero_raise_to_villain = 0

		for e in events:
			if not e.river_actions:
				continue
			hero_bet = False
			villain_bet = False
			hero_fold = False
			hero_raise = False
			villain_fold = False
			villain_raise = False
			for a in e.river_actions:
				if a.actor == "hero" and a.action == "B":
					hero_bet = True
				elif a.actor == "villain" and a.action == "B":
					villain_bet = True
				elif a.actor == "hero" and a.action == "F":
					hero_fold = True
				elif a.actor == "hero" and a.action == "R":
					hero_raise = True
				elif a.actor == "villain" and a.action == "F":
					villain_fold = True
				elif a.actor == "villain" and a.action == "R":
					villain_raise = True
			if hero_bet:
				hero_bet_n += 1
				if villain_fold:
					villain_fold_to_hero += 1
				if villain_raise:
					villain_raise_to_hero += 1
			if villain_bet:
				villain_bet_n += 1
				if hero_fold:
					hero_fold_to_villain += 1
				if hero_raise:
					hero_raise_to_villain += 1

		return {
			"hero_bet_pct": (hero_bet_n / n * 100) if n else 0,
			"villain_fold_to_hero_bet_pct": (villain_fold_to_hero / hero_bet_n * 100) if hero_bet_n else 0,
			"villain_raise_to_hero_bet_pct": (villain_raise_to_hero / hero_bet_n * 100) if hero_bet_n else 0,
			"villain_bet_pct": (villain_bet_n / n * 100) if n else 0,
			"hero_fold_to_villain_bet_pct": (hero_fold_to_villain / villain_bet_n * 100) if villain_bet_n else 0,
			"hero_raise_to_villain_bet_pct": (hero_raise_to_villain / villain_bet_n * 100) if villain_bet_n else 0,
		}

	BET_SIZE_BINS = [(0, 50), (50, 100), (100, 200)]

	ACTION_ORDER = ["X", "B0-50", "B50-100", "B100-200", "B200+",
		"C", "R0-50", "R50-100", "R100-200", "R200+", "F"]

	def _action_sort_key(self, action: str) -> int:
		try:
			return self.ACTION_ORDER.index(action)
		except ValueError:
			return len(self.ACTION_ORDER)

	def _compute_next_actions(self, events: list[LineEvent], depth: int, actions_attr: str = "flop_actions") -> list[dict]:
		action_groups: dict[str, list[float]] = {}
		for e in events:
			actions = getattr(e, actions_attr)
			if depth < len(actions):
				a = actions[depth]
				if a.action in ("B", "R") and a.size_pct is not None:
					# Bucket by size range
					placed = False
					for lo, hi in self.BET_SIZE_BINS:
						if lo <= a.size_pct < hi:
							key = f"{a.action}{lo}-{hi}"
							action_groups.setdefault(key, []).append(e.hero_pnl_bb)
							placed = True
							break
					if not placed:
						# Oversize (200%+)
						key = f"{a.action}200+"
						action_groups.setdefault(key, []).append(e.hero_pnl_bb)
				else:
					action_groups.setdefault(a.action, []).append(e.hero_pnl_bb)

		result = []
		for action in sorted(action_groups, key=self._action_sort_key):
			pnls = action_groups[action]
			result.append({
				"action": action,
				"ev": sum(pnls) / len(pnls) if pnls else 0,
				"count": len(pnls),
			})
		return result

	def _empty_flop_stats(self):
		return {k: 0 for k in ["cbet_pct", "fold_to_cbet_pct", "raise_to_cbet_pct", "fold_to_cbet_raise_pct", "donk_bet_pct", "fold_to_donk_pct", "raise_to_donk_pct", "fold_to_donk_raise_pct"]}

	def _empty_turn_stats(self):
		return {k: 0 for k in ["hero_bet_pct", "villain_fold_to_hero_bet_pct", "villain_raise_to_hero_bet_pct", "villain_bet_pct", "hero_fold_to_villain_bet_pct", "hero_raise_to_villain_bet_pct"]}

	def _empty_river_stats(self):
		return {k: 0 for k in ["hero_bet_pct", "villain_fold_to_hero_bet_pct", "villain_raise_to_hero_bet_pct", "villain_bet_pct", "hero_fold_to_villain_bet_pct", "hero_raise_to_villain_bet_pct"]}

	def _empty_ev_stats(self):
		return {"overall_ev": 0, "next_actions": []}

	def hand_type_distribution(self, f: LineFilter, flop_actions: list[str] | None = None, turn_actions: list[str] | None = None, river_actions: list[str] | None = None, start: date | None = None, end: date | None = None):
		from app.parsers.hand_types import classify_made_hand, classify_draw

		events = [e for e in self.events if _in_date_range(e.played_on, start, end) and e.filter(f)]

		if flop_actions:
			events = self._filter_by_street_prefix(events, "flop", flop_actions)

		on_turn = turn_actions is not None
		if on_turn:
			events = [e for e in events if e.turn_actions]
			if turn_actions:
				events = self._filter_by_street_prefix(events, "turn", turn_actions)

		on_river = river_actions is not None
		if on_river:
			events = [e for e in events if e.river_actions]
			if river_actions:
				events = self._filter_by_street_prefix(events, "river", river_actions)

		hero_made: dict[str, int] = {t.value: 0 for t in MadeHandType}
		hero_draws: dict[str, int] = {t.value: 0 for t in DrawType}
		villain_made: dict[str, int] = {t.value: 0 for t in MadeHandType}
		villain_draws: dict[str, int] = {t.value: 0 for t in DrawType}

		for e in events:
			board = list(e.flop_cards)
			if on_turn and e.turn_card:
				board.append(e.turn_card)
			if on_river and e.river_card:
				board.append(e.river_card)

			if e.hero_hand and board:
				hero_made[classify_made_hand(e.hero_hand, board).value] += 1
				hero_draws[classify_draw(e.hero_hand, board).value] += 1

			if e.villain_hand and board:
				villain_made[classify_made_hand(e.villain_hand, board).value] += 1
				villain_draws[classify_draw(e.villain_hand, board).value] += 1

		return {
			"hero": {
				"made_hands": hero_made,
				"draws": hero_draws,
			},
			"villain": {
				"made_hands": villain_made,
				"draws": villain_draws,
			},
		}


class Turns:
	def __init__(self):
		self.events: list[TurnEvent] = []

	def add_event(self, event: TurnEvent):
		self.events.append(event)

	def json(self, filters: TurnFilter, start: date | None = None, end: date | None = None):
		# Per-sequence counters
		counts: dict[str, dict[str, int]] = {}
		for seq in ActionSequence:
			counts[seq.value] = {
				"n": 0,
				"hero_bet": 0,
				"villain_fold_to_hero_bet": 0,
				"villain_raise_to_hero_bet": 0,
				"villain_bet": 0,
				"hero_fold_to_villain_bet": 0,
				"hero_raise_to_villain_bet": 0,
			}

		for e in self.events:
			if not _in_date_range(e.played_on, start, end):
				continue
			if not e.filter(filters):
				continue
			c = counts[e.flop_action_sequence.value]
			c["n"] += 1
			if e.hero_bet_turn:
				c["hero_bet"] += 1
				if e.villain_fold_to_hero_bet:
					c["villain_fold_to_hero_bet"] += 1
				if e.villain_raise_to_hero_bet:
					c["villain_raise_to_hero_bet"] += 1
			if e.villain_bet_turn:
				c["villain_bet"] += 1
				if e.hero_fold_to_villain_bet:
					c["hero_fold_to_villain_bet"] += 1
				if e.hero_raise_to_villain_bet:
					c["hero_raise_to_villain_bet"] += 1

		result = {}
		for seq in ActionSequence:
			c = counts[seq.value]
			n = c["n"]
			hb = c["hero_bet"]
			vb = c["villain_bet"]
			result[seq.value] = {
				"hero_bet_pct": (hb / n * 100) if n else 0,
				"villain_fold_to_hero_bet_pct": (c["villain_fold_to_hero_bet"] / hb * 100) if hb else 0,
				"villain_raise_to_hero_bet_pct": (c["villain_raise_to_hero_bet"] / hb * 100) if hb else 0,
				"villain_bet_pct": (vb / n * 100) if n else 0,
				"hero_fold_to_villain_bet_pct": (c["hero_fold_to_villain_bet"] / vb * 100) if vb else 0,
				"hero_raise_to_villain_bet_pct": (c["hero_raise_to_villain_bet"] / vb * 100) if vb else 0,
				"hand_count": n,
			}

		return result


class Rivers:

	def __init__(self):
		self.events: list[RiverEvent] = []

	def add_event(self, event: RiverEvent):
		self.events.append(event)

	def json(self, filters: RiverFilter, start: date | None = None, end: date | None = None):
		# Action counters
		n = 0
		hero_bet_count = 0
		villain_fold_to_hero = 0
		villain_raise_to_hero = 0
		villain_bet_count = 0
		hero_fold_to_villain = 0
		hero_raise_to_villain = 0

		# Per-sequence counters for showdown and avg pot
		seq_pot: dict[str, float] = {}
		seq_n: dict[str, int] = {}
		sd_bb: dict[str, float] = {}
		sd_n: dict[str, int] = {}
		for seq in ActionSequence:
			seq_pot[seq.value] = 0.0
			seq_n[seq.value] = 0
			sd_bb[seq.value] = 0.0
			sd_n[seq.value] = 0

		for e in self.events:
			if not _in_date_range(e.played_on, start, end):
				continue
			if not e.filter(filters):
				continue

			n += 1
			sv = e.river_action_sequence.value
			seq_n[sv] += 1
			seq_pot[sv] += e.pot_size_bb

			if e.hero_bet_river:
				hero_bet_count += 1
				if e.villain_fold_to_hero_bet:
					villain_fold_to_hero += 1
				if e.villain_raise_to_hero_bet:
					villain_raise_to_hero += 1
			if e.villain_bet_river:
				villain_bet_count += 1
				if e.hero_fold_to_villain_bet:
					hero_fold_to_villain += 1
				if e.hero_raise_to_villain_bet:
					hero_raise_to_villain += 1

			if e.went_to_showdown:
				sd_n[sv] += 1
				sd_bb[sv] += e.pot_size_bb if e.hero_won_showdown else -e.pot_size_bb

		showdown_result = {}
		avg_pot_result = {}
		for seq in ActionSequence:
			sv = seq.value
			if seq_n[sv]:
				avg_pot_result[sv] = {
					"avg_pot_bb": round(seq_pot[sv] / seq_n[sv], 1),
					"hand_count": seq_n[sv],
				}
			else:
				avg_pot_result[sv] = {"avg_pot_bb": 0, "hand_count": 0}

			if sd_n[sv]:
				showdown_result[sv] = {
					"bb_per_hand": round(sd_bb[sv] / sd_n[sv], 2),
					"hand_count": sd_n[sv],
				}
			else:
				showdown_result[sv] = {"bb_per_hand": 0, "hand_count": 0}

		return {
			"actions": {
				"hero_bet_pct": (hero_bet_count / n * 100) if n else 0,
				"villain_fold_to_hero_bet_pct": (villain_fold_to_hero / hero_bet_count * 100) if hero_bet_count else 0,
				"villain_raise_to_hero_bet_pct": (villain_raise_to_hero / hero_bet_count * 100) if hero_bet_count else 0,
				"villain_bet_pct": (villain_bet_count / n * 100) if n else 0,
				"hero_fold_to_villain_bet_pct": (hero_fold_to_villain / villain_bet_count * 100) if villain_bet_count else 0,
				"hero_raise_to_villain_bet_pct": (hero_raise_to_villain / villain_bet_count * 100) if villain_bet_count else 0,
				"hand_count": n,
			},
			"showdown": showdown_result,
			"avg_pot": avg_pot_result,
		}
