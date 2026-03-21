from .events import CBetEvent, LineEvent, TurnEvent, RiverEvent, FlopAction
from .filters import CBetFilter, LineFilter, TurnFilter, RiverFilter
from .enums import FlopActionSequence, RiverActionSequence


class CBets:
	def __init__(self):
		self.events: list[CBetEvent] = []

	def add_event(self, event: CBetEvent):
		self.events.append(event)

	def json(self, filters: CBetFilter):
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


	def bet_sizes(self, filters: CBetFilter):
		"""Return villain cbet sizes as list of pot-% values for distribution charting."""
		no_size_filter = CBetFilter(
			pot_types=filters.pot_types,
			board_types=filters.board_types,
			hero_preflop_raiser=filters.hero_preflop_raiser,
			hero_in_position=filters.hero_in_position,
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
		events = self.events
		if f.hero_in_position is not None:
			events = [e for e in events if e.hero_in_position == f.hero_in_position]
		if f.hero_preflop_raiser is not None:
			events = [e for e in events if e.hero_preflop_raiser == f.hero_preflop_raiser]
		events = [e for e in events if e.pot_type in f.pot_types]
		events = [e for e in events if e.board_type in f.board_types]
		return events

	def flop_spot_stats(self, f: LineFilter, action_prefix: list[str] | None = None):
		events = self._filter(f)

		# Filter by action prefix if provided
		if action_prefix:
			events = self._filter_by_action_prefix(events, action_prefix)

		if not events:
			return {
				"hand_count": 0,
				"street_stats": self._empty_street_stats(),
				"ev_stats": self._empty_ev_stats(),
				"bet_sizes": [],
				"next_actor": None,
				"action_depth": len(action_prefix) if action_prefix else 0,
			}

		n = len(events)
		depth = len(action_prefix) if action_prefix else 0

		# Street stats (always computed from full filtered set)
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

		# Dynamic next actions at current depth
		next_actions = self._compute_next_actions(events, depth)
		overall_ev = (sum(e.hero_pnl_bb for e in events) / n) if n else 0

		# Determine next actor
		next_actor = None
		for e in events:
			if depth < len(e.flop_actions):
				next_actor = e.flop_actions[depth].actor
				break

		# Bet sizes for next actor's bets
		bet_sizes = []
		for e in events:
			if depth < len(e.flop_actions):
				a = e.flop_actions[depth]
				if a.action in ("B", "R") and a.size_pct is not None:
					bet_sizes.append(a.size_pct)

		return {
			"hand_count": n,
			"street_stats": {
				"cbet_pct": cbet_pct,
				"fold_to_cbet_pct": fold_to_cbet_pct,
				"raise_to_cbet_pct": raise_to_cbet_pct,
				"fold_to_cbet_raise_pct": fold_to_cbet_raise_pct,
				"donk_bet_pct": donk_pct,
				"fold_to_donk_pct": fold_to_donk_pct,
				"raise_to_donk_pct": raise_to_donk_pct,
				"fold_to_donk_raise_pct": fold_to_donk_raise_pct,
			},
			"ev_stats": {
				"overall_ev": overall_ev,
				"next_actions": next_actions,
			},
			"bet_sizes": [round(s, 1) for s in bet_sizes],
			"next_actor": next_actor,
			"action_depth": depth,
		}

	def _filter_by_action_prefix(self, events: list[LineEvent], prefix: list[str]) -> list[LineEvent]:
		"""Filter events whose flop_actions match the given action prefix.
		
		Each prefix entry is: "X", "F", "C", or "Bmin-max" / "Rmin-max" for sized actions.
		"""
		result = []
		for e in events:
			if len(e.flop_actions) < len(prefix):
				continue
			match = True
			for i, p in enumerate(prefix):
				a = e.flop_actions[i]
				if p in ("X", "F", "C"):
					if a.action != p:
						match = False
						break
				elif p.startswith("B") or p.startswith("R"):
					expected_action = p[0]
					if a.action != expected_action:
						match = False
						break
					# Parse size range (e.g. "B40-80" or "B200+")
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

	BET_SIZE_BINS = [(0, 50), (50, 100), (100, 200)]

	ACTION_ORDER = ["X", "B0-50", "B50-100", "B100-200", "B200+",
		"C", "R0-50", "R50-100", "R100-200", "R200+", "F"]

	def _action_sort_key(self, action: str) -> int:
		try:
			return self.ACTION_ORDER.index(action)
		except ValueError:
			return len(self.ACTION_ORDER)

	def _compute_next_actions(self, events: list[LineEvent], depth: int) -> list[dict]:
		"""Compute EV and count for each possible next action at the given depth.
		Bet/Raise actions are split into size buckets."""
		action_groups: dict[str, list[float]] = {}
		for e in events:
			if depth < len(e.flop_actions):
				a = e.flop_actions[depth]
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

	def _empty_street_stats(self):
		return {k: 0 for k in ["cbet_pct", "fold_to_cbet_pct", "raise_to_cbet_pct", "fold_to_cbet_raise_pct", "donk_bet_pct", "fold_to_donk_pct", "raise_to_donk_pct", "fold_to_donk_raise_pct"]}

	def _empty_ev_stats(self):
		return {"overall_ev": 0, "next_actions": []}


class Turns:
	def __init__(self):
		self.events: list[TurnEvent] = []

	def add_event(self, event: TurnEvent):
		self.events.append(event)

	def json(self, filters: TurnFilter):
		result = {}
		
		for sequence in FlopActionSequence:
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
				for seq in RiverActionSequence
			}
			empty_avg_pot = {
				seq.value: {"avg_pot_bb": 0, "hand_count": 0}
				for seq in RiverActionSequence
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
		for seq in RiverActionSequence:
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
