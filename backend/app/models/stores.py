from .events import FlopEvent, LineEvent, TurnEvent, RiverEvent
from .filters import FlopFilter, LineFilter, TurnFilter, RiverFilter
from .enums import ActionSequence


class Flops:
	def __init__(self):
		self.events: list[FlopEvent] = []

	def add_event(self, event: FlopEvent):
		self.events.append(event)

	def json(self, filters: FlopFilter):
		events = [e for e in self.events if e.filter(filters)]
		
		if not events:
			return { "cbet_pct": 0, "fcbet_pct": 0, "raise_to_cbet_pct": 0, "donk_bet_pct": 0, "fold_to_donk_pct": 0, "raise_to_donk_pct": 0, "hand_count": 0 }

		cbet_pct = sum(1 for e in events if e.cbet) / len(events)
		cbet_events = [e for e in events if e.cbet]
		fcbet_pct = (sum(1 for e in cbet_events if e.fold_to_cbet) / len(cbet_events)) if cbet_events else 0
		raise_to_cbet_pct = (sum(1 for e in cbet_events if e.raise_to_cbet) / len(cbet_events)) if cbet_events else 0
		
		donk_pct = sum(1 for e in events if e.donk_bet) / len(events)
		donk_events = [e for e in events if e.donk_bet]
		fold_to_donk_pct = (sum(1 for e in donk_events if e.fold_to_donk_bet) / len(donk_events)) if donk_events else 0
		raise_to_donk_pct = (sum(1 for e in donk_events if e.raise_to_donk_bet) / len(donk_events)) if donk_events else 0
		
		return {
			"cbet_pct": cbet_pct * 100,
			"fcbet_pct": fcbet_pct * 100,
			"raise_to_cbet_pct": raise_to_cbet_pct * 100,
			"donk_bet_pct": donk_pct * 100,
			"fold_to_donk_pct": fold_to_donk_pct * 100,
			"raise_to_donk_pct": raise_to_donk_pct * 100,
			"hand_count": len(events),
		}


	def bet_sizes(self, filters: FlopFilter):
		"""Return villain cbet sizes as list of pot-% values for distribution charting."""
		no_size_filter = FlopFilter(
			pot_types=filters.pot_types,
			board_types=filters.board_types,
			hero_preflop_raiser=filters.hero_preflop_raiser,
			hero_in_position=filters.hero_in_position,
			include_pool=filters.include_pool,
		)
		events = [e for e in self.events if e.filter(no_size_filter)]
		# Villain cbet = when hero is DEF (not PFR) and villain cbets
		sizes = []
		for e in events:
			if not e.hero_preflop_raiser and e.cbet_size_pct is not None:
				sizes.append(round(e.cbet_size_pct, 1))
		return sizes


class LineEvents:
	def __init__(self):
		self.events: list[LineEvent] = []

	def add_event(self, event: LineEvent):
		self.events.append(event)

	def _filter(self, f: LineFilter) -> list[LineEvent]:
		return [e for e in self.events if e.filter(f)]

	def spot_stats(self, f: LineFilter, flop_actions: list[str] | None = None, turn_actions: list[str] | None = None, river_actions: list[str] | None = None):
		events = self._filter(f)

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
		overall_ev = sum(e.hero_pnl_bb for e in events) / n

		next_actor = None
		for e in events:
			actions = getattr(e, actions_attr)
			if depth < len(actions):
				next_actor = actions[depth].actor
				break

		bet_sizes = []
		for e in events:
			actions = getattr(e, actions_attr)
			if depth < len(actions):
				a = actions[depth]
				if a.action in ("B", "R") and a.size_pct is not None:
					bet_sizes.append(a.size_pct)

		flop_complete = not on_turn and not on_river and next_actions == [] and any(e.turn_actions for e in events)
		turn_available = any(e.turn_actions for e in events)
		turn_complete = on_turn and not on_river and next_actions == [] and any(e.river_actions for e in events)
		river_available = any(e.river_actions for e in events)

		TOP_N = 5
		sorted_by_pnl = sorted(events, key=lambda e: e.hero_pnl_bb, reverse=True)
		top_wins = [self._build_hand_result(e) for e in sorted_by_pnl[:TOP_N]]
		top_losses = [self._build_hand_result(e) for e in sorted_by_pnl[-TOP_N:][::-1]]

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
			"turn_available": turn_available,
			"turn_complete": turn_complete or on_river,
			"river_available": river_available,
			"top_wins": top_wins,
			"top_losses": top_losses,
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
		cbet_events = [e for e in events if e.cbet]
		donk_events = [e for e in events if e.donk_bet]
		cbet_pct = (len(cbet_events) / n) * 100 if n else 0
		donk_pct = (len(donk_events) / n) * 100 if n else 0
		fold_to_cbet_pct = (sum(1 for e in cbet_events if e.fold_to_cbet) / len(cbet_events) * 100) if cbet_events else 0
		raise_to_cbet_pct = (sum(1 for e in cbet_events if e.raise_to_cbet) / len(cbet_events) * 100) if cbet_events else 0
		fold_to_cbet_raise_pct = (sum(1 for e in cbet_events if e.fold_to_cbet_raise) / max(1, sum(1 for e in cbet_events if e.raise_to_cbet)) * 100) if cbet_events else 0
		fold_to_donk_pct = (sum(1 for e in donk_events if e.fold_to_donk_bet) / len(donk_events) * 100) if donk_events else 0
		raise_to_donk_pct = (sum(1 for e in donk_events if e.raise_to_donk_bet) / len(donk_events) * 100) if donk_events else 0
		fold_to_donk_raise_pct = (sum(1 for e in donk_events if e.fold_to_donk_raise) / max(1, sum(1 for e in donk_events if e.raise_to_donk_bet)) * 100) if donk_events else 0

		return {
			"cbet_pct": cbet_pct,
			"fold_to_cbet_pct": fold_to_cbet_pct,
			"raise_to_cbet_pct": raise_to_cbet_pct,
			"fold_to_cbet_raise_pct": fold_to_cbet_raise_pct,
			"donk_bet_pct": donk_pct,
			"fold_to_donk_pct": fold_to_donk_pct,
			"raise_to_donk_pct": raise_to_donk_pct,
			"fold_to_donk_raise_pct": fold_to_donk_raise_pct,
		}

	def _compute_turn_stats(self, events: list[LineEvent]) -> dict:
		n = len(events)
		hero_bet_events = [e for e in events if e.turn_actions and any(a.actor == "hero" and a.action == "B" for a in e.turn_actions)]
		villain_bet_events = [e for e in events if e.turn_actions and any(a.actor == "villain" and a.action == "B" for a in e.turn_actions)]
		hero_bet_pct = (len(hero_bet_events) / n) * 100 if n else 0
		villain_bet_pct = (len(villain_bet_events) / n) * 100 if n else 0

		villain_fold_to_hero_bet_pct = 0
		villain_raise_to_hero_bet_pct = 0
		if hero_bet_events:
			villain_fold_to_hero_bet_pct = sum(1 for e in hero_bet_events if any(a.actor == "villain" and a.action == "F" for a in e.turn_actions)) / len(hero_bet_events) * 100
			villain_raise_to_hero_bet_pct = sum(1 for e in hero_bet_events if any(a.actor == "villain" and a.action == "R" for a in e.turn_actions)) / len(hero_bet_events) * 100

		hero_fold_to_villain_bet_pct = 0
		hero_raise_to_villain_bet_pct = 0
		if villain_bet_events:
			hero_fold_to_villain_bet_pct = sum(1 for e in villain_bet_events if any(a.actor == "hero" and a.action == "F" for a in e.turn_actions)) / len(villain_bet_events) * 100
			hero_raise_to_villain_bet_pct = sum(1 for e in villain_bet_events if any(a.actor == "hero" and a.action == "R" for a in e.turn_actions)) / len(villain_bet_events) * 100

		return {
			"hero_bet_pct": hero_bet_pct,
			"villain_fold_to_hero_bet_pct": villain_fold_to_hero_bet_pct,
			"villain_raise_to_hero_bet_pct": villain_raise_to_hero_bet_pct,
			"villain_bet_pct": villain_bet_pct,
			"hero_fold_to_villain_bet_pct": hero_fold_to_villain_bet_pct,
			"hero_raise_to_villain_bet_pct": hero_raise_to_villain_bet_pct,
		}

	def _compute_river_stats(self, events: list[LineEvent]) -> dict:
		n = len(events)
		hero_bet_events = [e for e in events if e.river_actions and any(a.actor == "hero" and a.action == "B" for a in e.river_actions)]
		villain_bet_events = [e for e in events if e.river_actions and any(a.actor == "villain" and a.action == "B" for a in e.river_actions)]
		hero_bet_pct = (len(hero_bet_events) / n) * 100 if n else 0
		villain_bet_pct = (len(villain_bet_events) / n) * 100 if n else 0

		villain_fold_to_hero_bet_pct = 0
		villain_raise_to_hero_bet_pct = 0
		if hero_bet_events:
			villain_fold_to_hero_bet_pct = sum(1 for e in hero_bet_events if any(a.actor == "villain" and a.action == "F" for a in e.river_actions)) / len(hero_bet_events) * 100
			villain_raise_to_hero_bet_pct = sum(1 for e in hero_bet_events if any(a.actor == "villain" and a.action == "R" for a in e.river_actions)) / len(hero_bet_events) * 100

		hero_fold_to_villain_bet_pct = 0
		hero_raise_to_villain_bet_pct = 0
		if villain_bet_events:
			hero_fold_to_villain_bet_pct = sum(1 for e in villain_bet_events if any(a.actor == "hero" and a.action == "F" for a in e.river_actions)) / len(villain_bet_events) * 100
			hero_raise_to_villain_bet_pct = sum(1 for e in villain_bet_events if any(a.actor == "hero" and a.action == "R" for a in e.river_actions)) / len(villain_bet_events) * 100

		return {
			"hero_bet_pct": hero_bet_pct,
			"villain_fold_to_hero_bet_pct": villain_fold_to_hero_bet_pct,
			"villain_raise_to_hero_bet_pct": villain_raise_to_hero_bet_pct,
			"villain_bet_pct": villain_bet_pct,
			"hero_fold_to_villain_bet_pct": hero_fold_to_villain_bet_pct,
			"hero_raise_to_villain_bet_pct": hero_raise_to_villain_bet_pct,
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


class Turns:
	def __init__(self):
		self.events: list[TurnEvent] = []

	def add_event(self, event: TurnEvent):
		self.events.append(event)

	def json(self, filters: TurnFilter):
		result = {}
		
		for sequence in ActionSequence:
			sequence_events = [e for e in self.events if e.flop_action_sequence == sequence and e.filter(filters)]
			
			if not sequence_events:
				result[sequence.value] = {
					"hero_bet_pct": 0,
					"villain_fold_to_hero_bet_pct": 0,
					"villain_raise_to_hero_bet_pct": 0,
					"villain_bet_pct": 0,
					"hero_fold_to_villain_bet_pct": 0,
					"hero_raise_to_villain_bet_pct": 0,
					"hand_count": 0,
				}
				continue
			
			hero_bet_pct = sum(1 for e in sequence_events if e.hero_bet_turn) / len(sequence_events)
			hero_bet_events = [e for e in sequence_events if e.hero_bet_turn]
			villain_fold_to_hero_bet_pct = (sum(1 for e in hero_bet_events if e.villain_fold_to_hero_bet) / len(hero_bet_events)) if hero_bet_events else 0
			villain_raise_to_hero_bet_pct = (sum(1 for e in hero_bet_events if e.villain_raise_to_hero_bet) / len(hero_bet_events)) if hero_bet_events else 0
			
			villain_bet_pct = sum(1 for e in sequence_events if e.villain_bet_turn) / len(sequence_events)
			villain_bet_events = [e for e in sequence_events if e.villain_bet_turn]
			hero_fold_to_villain_bet_pct = (sum(1 for e in villain_bet_events if e.hero_fold_to_villain_bet) / len(villain_bet_events)) if villain_bet_events else 0
			hero_raise_to_villain_bet_pct = (sum(1 for e in villain_bet_events if e.hero_raise_to_villain_bet) / len(villain_bet_events)) if villain_bet_events else 0
			
			result[sequence.value] = {
				"hero_bet_pct": hero_bet_pct * 100,
				"villain_fold_to_hero_bet_pct": villain_fold_to_hero_bet_pct * 100,
				"villain_raise_to_hero_bet_pct": villain_raise_to_hero_bet_pct * 100,
				"villain_bet_pct": villain_bet_pct * 100,
				"hero_fold_to_villain_bet_pct": hero_fold_to_villain_bet_pct * 100,
				"hero_raise_to_villain_bet_pct": hero_raise_to_villain_bet_pct * 100,
				"hand_count": len(sequence_events),
			}
		
		return result


class Rivers:
	def __init__(self):
		self.events: list[RiverEvent] = []

	def add_event(self, event: RiverEvent):
		self.events.append(event)

	def json(self, filters: RiverFilter):
		events = [e for e in self.events if e.filter(filters)]

		if not events:
			empty_showdown = {
				seq.value: {"bb_per_hand": 0, "hand_count": 0}
				for seq in ActionSequence
			}
			empty_avg_pot = {
				seq.value: {"avg_pot_bb": 0, "hand_count": 0}
				for seq in ActionSequence
			}
			return {
				"actions": {
					"hero_bet_pct": 0,
					"villain_fold_to_hero_bet_pct": 0,
					"villain_raise_to_hero_bet_pct": 0,
					"villain_bet_pct": 0,
					"hero_fold_to_villain_bet_pct": 0,
					"hero_raise_to_villain_bet_pct": 0,
					"hand_count": 0,
				},
				"showdown": empty_showdown,
				"avg_pot": empty_avg_pot,
			}

		hero_bet_pct = sum(1 for e in events if e.hero_bet_river) / len(events)
		hero_bet_events = [e for e in events if e.hero_bet_river]
		villain_fold_pct = (sum(1 for e in hero_bet_events if e.villain_fold_to_hero_bet) / len(hero_bet_events)) if hero_bet_events else 0
		villain_raise_pct = (sum(1 for e in hero_bet_events if e.villain_raise_to_hero_bet) / len(hero_bet_events)) if hero_bet_events else 0

		villain_bet_pct = sum(1 for e in events if e.villain_bet_river) / len(events)
		villain_bet_events = [e for e in events if e.villain_bet_river]
		hero_fold_pct = (sum(1 for e in villain_bet_events if e.hero_fold_to_villain_bet) / len(villain_bet_events)) if villain_bet_events else 0
		hero_raise_pct = (sum(1 for e in villain_bet_events if e.hero_raise_to_villain_bet) / len(villain_bet_events)) if villain_bet_events else 0

		showdown_result = {}
		avg_pot_result = {}
		for seq in ActionSequence:
			seq_events = [e for e in events if e.river_action_sequence == seq]
			if not seq_events:
				avg_pot_result[seq.value] = {"avg_pot_bb": 0, "hand_count": 0}
			else:
				total_pot = sum(e.pot_size_bb for e in seq_events)
				avg_pot_result[seq.value] = {
					"avg_pot_bb": round(total_pot / len(seq_events), 1),
					"hand_count": len(seq_events),
				}

			sd_events = [e for e in events if e.went_to_showdown and e.river_action_sequence == seq]
			if not sd_events:
				showdown_result[seq.value] = {"bb_per_hand": 0, "hand_count": 0}
				continue
			total_bb = sum(e.pot_size_bb if e.hero_won_showdown else -e.pot_size_bb for e in sd_events)
			showdown_result[seq.value] = {
				"bb_per_hand": round(total_bb / len(sd_events), 2),
				"hand_count": len(sd_events),
			}

		return {
			"actions": {
				"hero_bet_pct": hero_bet_pct * 100,
				"villain_fold_to_hero_bet_pct": villain_fold_pct * 100,
				"villain_raise_to_hero_bet_pct": villain_raise_pct * 100,
				"villain_bet_pct": villain_bet_pct * 100,
				"hero_fold_to_villain_bet_pct": hero_fold_pct * 100,
				"hero_raise_to_villain_bet_pct": hero_raise_pct * 100,
				"hand_count": len(events),
			},
			"showdown": showdown_result,
			"avg_pot": avg_pot_result,
		}
