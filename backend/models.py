from datetime import date

from playing_cards_lib.core import Rank
from playing_cards_lib.poker import PokerPosition, PotType, BoardType


class Stats:
	def __init__(self):
		self.folds = 0
		self.raises = 0
		self.calls = 0

	def json(self):
		return {
			"folds": self.folds,
			"raises": self.raises,
			"calls": self.calls
		}


class Range:
	def __init__(self):
		self.hands: dict[str, Stats] = self._initialise_hands()

	def add(self, hand_key: str, action: str):
		if hand_key not in self.hands:
			print(f"Error: unknown hole cards {hand_key}")
			return
		
		stats = self.hands[hand_key]
		if action.lower() == "folds":
			stats.folds += 1
		elif action.lower() == "raises":
			stats.raises += 1
		elif action.lower() == "calls":
			stats.calls += 1
		else:
			print(f"Error: unknown action {action}")

	def json(self):
		return { key: stats.json() for key, stats in self.hands.items() }

	def _initialise_hands(self):
		hands = {}
		for fst_rank in Rank:
			passed = False
			for snd_rank in Rank:
				key = ""
				if fst_rank == snd_rank:
					key = f"{fst_rank.value}{snd_rank.value}"
					passed = True
				elif passed:
					key = f"{snd_rank.value}{fst_rank.value}s"
				else:
					key = f"{fst_rank.value}{snd_rank.value}o"
				hands[key] = Stats()
		return hands


class SrpRanges:
	def __init__(self):
		self.ranges = {
			PokerPosition.LJ: Range(),
			PokerPosition.HJ: Range(),
			PokerPosition.CO: Range(),
			PokerPosition.BTN: Range(),
			PokerPosition.SB: Range()
        }

	def add_hand(self, hand_key, position, action):
		if position not in self.ranges:
			print(f"Error: invalid rfi position {position}")
		self.ranges[position].add(hand_key, action)
	
	def json(self):
		return {k.name: v.json() for k, v in self.ranges.items()}


class ThreeBetRanges:
	def __init__(self):
		self.ranges = {
			PokerPosition.LJ: Range(),
			PokerPosition.HJ: Range(),
			PokerPosition.CO: Range(),
			PokerPosition.BTN: Range(),
			PokerPosition.SB: Range(),
        }

	def add_hand(self, hand_key, position, action):
		if position not in self.ranges:
			print(f"Error: invalid rfi position {position}")
		self.ranges[position].add(hand_key, action)
	
	def json(self):
		return {k.name: v.json() for k, v in self.ranges.items()}


class FourBetRanges:
	def __init__(self):
		self.ranges = {
			PokerPosition.LJ: Range(),
			PokerPosition.HJ: Range(),
			PokerPosition.CO: Range(),
			PokerPosition.BTN: Range(),
			PokerPosition.SB: Range(),
			PokerPosition.BB: Range()
        }

	def add_hand(self, hand_key, position, action):
		if position not in self.ranges:
			print(f"Error: invalid rfi position {position}")
		self.ranges[position].add(hand_key, action)
	
	def json(self):
		return {k.name: v.json() for k, v in self.ranges.items()}


class Ranges:
	def __init__(self):
		self.ranges = {
			PotType.SRP: SrpRanges(),
			PotType.THREE_BET: ThreeBetRanges(),
			PotType.FOUR_BET: FourBetRanges()
		}

	def add_hand(self, hand_key, position, action, pot_type, villain):
		if pot_type == PotType.THREE_BET:
			self.ranges[PotType.THREE_BET].add_hand(hand_key, villain, action)
		else:
			self.ranges[pot_type].add_hand(hand_key, position, action)

	def json(self):
		return { k.name: v.json() for k, v in self.ranges.items() }


class CBetFilter:
	def __init__(
		self,
		pot_types: list[PotType] | None = None,
		board_types: list[BoardType] | None = None,
		hero_preflop_raiser: list[bool] | None = None,
		hero_in_position: list[bool] | None = None,
	):
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.hero_preflop_raiser = hero_preflop_raiser if hero_preflop_raiser is not None else [True, False]
		self.hero_in_position = hero_in_position if hero_in_position is not None else [True, False]


class CBetEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_preflop_raiser: bool
	hero_in_position: bool
	cbet: bool
	fold_to_cbet: bool
	donk_bet: bool
	fold_to_donk_bet: bool

	def filter(self, filters: CBetFilter) -> bool:
		if self.pot_type not in filters.pot_types:
			return False
		if self.board_type not in filters.board_types:
			return False
		if self.hero_preflop_raiser not in filters.hero_preflop_raiser:
			return False
		if self.hero_in_position not in filters.hero_in_position:
			return False
		return True


class RangeEvent:
	played_on: date
	hand_key: str
	position: PokerPosition
	action: str
	pot_type: PotType
	villain: PokerPosition | None


class CBets:
	def __init__(self):
		self.events: list[CBetEvent] = []

	def add_event(self, event: CBetEvent):
		self.events.append(event)

	def json(self, filters: CBetFilter):
		events = [e for e in self.events if e.filter(filters)]
		
		if not events:
			return { "cbet_pct": 0, "fcbet_pct": 0, "donk_bet_pct": 0, "fold_to_donk_pct": 0, "hand_count": 0 }

		cbet_pct = sum(1 for e in events if e.cbet) / len(events)
		cbet_events = [e for e in events if e.cbet]
		fcbet_pct = (sum(1 for e in cbet_events if e.fold_to_cbet) / len(cbet_events)) if cbet_events else 0
		donk_pct = sum(1 for e in events if e.donk_bet) / len(events)
		donk_events = [e for e in events if e.donk_bet]
		fold_to_donk_pct = (sum(1 for e in donk_events if e.fold_to_donk_bet) / len(donk_events)) if donk_events else 0
		return {
			"cbet_pct": cbet_pct * 100,
			"fcbet_pct": fcbet_pct * 100,
			"donk_bet_pct": donk_pct * 100,
			"fold_to_donk_pct": fold_to_donk_pct * 100,
			"hand_count": len(events),
		}
