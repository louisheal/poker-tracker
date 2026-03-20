from datetime import date
from enum import Enum

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
		bet_size_min: float | None = None,
		bet_size_max: float | None = None,
	):
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.hero_preflop_raiser = hero_preflop_raiser if hero_preflop_raiser is not None else [True, False]
		self.hero_in_position = hero_in_position if hero_in_position is not None else [True, False]
		self.bet_size_min = bet_size_min
		self.bet_size_max = bet_size_max


class CBetEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_preflop_raiser: bool
	hero_in_position: bool
	cbet: bool
	fold_to_cbet: bool
	raise_to_cbet: bool
	donk_bet: bool
	fold_to_donk_bet: bool
	raise_to_donk_bet: bool
	cbet_size_pct: float | None
	donk_bet_size_pct: float | None

	def __init__(self):
		self.cbet_size_pct = None
		self.donk_bet_size_pct = None

	def filter(self, filters: CBetFilter) -> bool:
		if self.pot_type not in filters.pot_types:
			return False
		if self.board_type not in filters.board_types:
			return False
		if self.hero_preflop_raiser not in filters.hero_preflop_raiser:
			return False
		if self.hero_in_position not in filters.hero_in_position:
			return False
		if filters.bet_size_min is not None or filters.bet_size_max is not None:
			# Determine the relevant bet size for this hand
			bet_pct = self.cbet_size_pct if self.cbet else self.donk_bet_size_pct if self.donk_bet else None
			if bet_pct is not None:
				lo = filters.bet_size_min if filters.bet_size_min is not None else 0
				hi = filters.bet_size_max if filters.bet_size_max is not None else 200
				if bet_pct < lo or bet_pct > hi:
					return False
			# Hands with no bet (XX) pass through — no bet size to filter on
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


class FlopActionSequence(str, Enum):
	XX = "XX"
	XBC = "XBC"
	XBRC = "XBRC"
	BC = "BC"


class TurnRunout(str, Enum):
	OVERCARD = "OVERCARD"
	FLUSH_COMPLETING = "FLUSH_COMPLETING"
	PAIRED = "PAIRED"
	OTHER = "OTHER"


class RiverRunout(str, Enum):
	OVERCARD = "OVERCARD"
	FLUSH_COMPLETING = "FLUSH_COMPLETING"
	PAIRED = "PAIRED"
	OTHER = "OTHER"


class FlopRankTexture(str, Enum):
	TRIPS = "TRIPS"
	PAIRED = "PAIRED"
	UNPAIRED = "UNPAIRED"


class TurnActionSequence(str, Enum):
	XX = "XX"
	XBC = "XBC"
	XBRC = "XBRC"
	BC = "BC"


class RiverActionSequence(str, Enum):
	XX = "XX"
	XBC = "XBC"
	XBRC = "XBRC"
	BC = "BC"


class TurnEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_preflop_raiser: bool
	hero_in_position: bool
	flop_action_sequence: FlopActionSequence
	turn_runout: TurnRunout
	hero_bet_turn: bool
	villain_fold_to_hero_bet: bool
	villain_raise_to_hero_bet: bool
	villain_bet_turn: bool
	hero_fold_to_villain_bet: bool
	hero_raise_to_villain_bet: bool

	def filter(self, filters: "TurnFilter") -> bool:
		if self.pot_type not in filters.pot_types:
			return False
		if self.board_type not in filters.board_types:
			return False
		if self.hero_preflop_raiser not in filters.hero_preflop_raiser:
			return False
		if self.hero_in_position not in filters.hero_in_position:
			return False
		if self.turn_runout not in filters.turn_runouts:
			return False
		return True


class TurnFilter:
	def __init__(
		self,
		pot_types: list[PotType] | None = None,
		board_types: list[BoardType] | None = None,
		hero_preflop_raiser: list[bool] | None = None,
		hero_in_position: list[bool] | None = None,
		turn_runouts: list[TurnRunout] | None = None,
	):
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.hero_preflop_raiser = hero_preflop_raiser if hero_preflop_raiser is not None else [True, False]
		self.hero_in_position = hero_in_position if hero_in_position is not None else [True, False]
		self.turn_runouts = turn_runouts if turn_runouts is not None else list(TurnRunout)


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


class ShowdownType(str, Enum):
	CHECK_CHECK = "CHECK_CHECK"
	BET_CALL = "BET_CALL"
	RAISE_OCCURRED = "RAISE_OCCURRED"


class RiverEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_in_position: bool
	flop_action_sequence: FlopActionSequence
	flop_rank_texture: FlopRankTexture
	turn_runout: TurnRunout
	turn_action_sequence: TurnActionSequence
	river_runout: RiverRunout
	river_action_sequence: RiverActionSequence
	hero_bet_river: bool
	villain_fold_to_hero_bet: bool
	villain_raise_to_hero_bet: bool
	villain_bet_river: bool
	hero_fold_to_villain_bet: bool
	hero_raise_to_villain_bet: bool
	went_to_showdown: bool
	showdown_type: ShowdownType | None
	hero_won_showdown: bool
	pot_size_bb: float

	def filter(self, filters: "RiverFilter") -> bool:
		if self.pot_type not in filters.pot_types:
			return False
		if self.board_type not in filters.board_types:
			return False
		if self.hero_in_position not in filters.hero_in_position:
			return False
		if self.flop_action_sequence not in filters.flop_actions:
			return False
		if self.flop_rank_texture not in filters.flop_rank_textures:
			return False
		if self.turn_runout not in filters.turn_runouts:
			return False
		if self.turn_action_sequence not in filters.turn_action_sequences:
			return False
		if self.river_runout not in filters.river_runouts:
			return False
		return True


class RiverFilter:
	def __init__(
		self,
		pot_types: list[PotType] | None = None,
		board_types: list[BoardType] | None = None,
		hero_in_position: list[bool] | None = None,
		flop_actions: list[FlopActionSequence] | None = None,
		flop_rank_textures: list[FlopRankTexture] | None = None,
		turn_runouts: list[TurnRunout] | None = None,
		turn_action_sequences: list[TurnActionSequence] | None = None,
		river_runouts: list[RiverRunout] | None = None,
	):
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.hero_in_position = hero_in_position if hero_in_position is not None else [True, False]
		self.flop_actions = flop_actions if flop_actions is not None else list(FlopActionSequence)
		self.flop_rank_textures = flop_rank_textures if flop_rank_textures is not None else list(FlopRankTexture)
		self.turn_runouts = turn_runouts if turn_runouts is not None else list(TurnRunout)
		self.turn_action_sequences = turn_action_sequences if turn_action_sequences is not None else list(TurnActionSequence)
		self.river_runouts = river_runouts if river_runouts is not None else list(RiverRunout)


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
