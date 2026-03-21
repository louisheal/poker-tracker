from dataclasses import dataclass, field
from datetime import date

from playing_cards_lib.poker import PokerPosition, PotType, BoardType

from .enums import FlopActionSequence, TurnRunout, RiverRunout, FlopRankTexture, TurnActionSequence, RiverActionSequence, ShowdownType


class RangeEvent:
	played_on: date
	hand_key: str
	position: PokerPosition
	action: str
	pot_type: PotType
	villain: PokerPosition | None


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

	def filter(self, filters) -> bool:
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


@dataclass
class FlopAction:
	actor: str           # "hero" or "villain"
	action: str          # "X" (check), "B" (bet), "C" (call), "R" (raise), "F" (fold)
	size_pct: float | None = None  # pot-relative % for B/R, None for X/C/F


class LineEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_in_position: bool
	hero_preflop_raiser: bool
	hero_pnl_bb: float
	hero_preflop_invested_bb: float
	pot_at_flop_bb: float
	flop_actions: list[FlopAction]
	# Legacy cbet/donk stats for StreetStatsPanel
	cbet: bool
	fold_to_cbet: bool
	raise_to_cbet: bool
	donk_bet: bool
	fold_to_donk_bet: bool
	raise_to_donk_bet: bool
	cbet_size_pct: float | None
	donk_bet_size_pct: float | None
	fold_to_cbet_raise: bool
	fold_to_donk_raise: bool

	def __init__(self):
		self.flop_actions = []
		self.cbet_size_pct = None
		self.donk_bet_size_pct = None
		self.fold_to_cbet_raise = False
		self.fold_to_donk_raise = False
		self.hero_preflop_invested_bb = 0.0


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
