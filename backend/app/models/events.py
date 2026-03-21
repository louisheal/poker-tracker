from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from playing_cards_lib.poker import PokerPosition

from .enums import ActionSequence, Runout, FlopRankTexture, ShowdownType, BoardType, PotType

if TYPE_CHECKING:
	from .filters import FlopFilter, TurnFilter, RiverFilter


@dataclass
class RangeEvent:
	played_on: date
	hand_key: str
	position: PokerPosition
	action: str
	pot_type: PotType
	villain: PokerPosition | None


@dataclass
class FlopEvent:
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
	cbet_size_pct: float | None = None
	donk_bet_size_pct: float | None = None

	def filter(self, filters: "FlopFilter") -> bool:
		if self.pot_type not in filters.pot_types:
			return False
		if self.board_type not in filters.board_types:
			return False
		if self.hero_preflop_raiser not in filters.hero_preflop_raiser:
			return False
		if self.hero_in_position not in filters.hero_in_position:
			return False
		if filters.bet_size_min is not None or filters.bet_size_max is not None:
			bet_pct = self.cbet_size_pct if self.cbet else self.donk_bet_size_pct if self.donk_bet else None
			if bet_pct is not None:
				lo = filters.bet_size_min if filters.bet_size_min is not None else 0
				hi = filters.bet_size_max if filters.bet_size_max is not None else 200
				if bet_pct < lo or bet_pct > hi:
					return False
		return True


@dataclass
class FlopAction:
	actor: str
	action: str
	size_pct: float | None = None


@dataclass
class LineEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_in_position: bool
	hero_preflop_raiser: bool
	hero_pnl_bb: float
	hero_preflop_invested_bb: float
	pot_at_flop_bb: float
	flop_actions: list[FlopAction] = field(default_factory=list)
	cbet: bool = False
	fold_to_cbet: bool = False
	raise_to_cbet: bool = False
	donk_bet: bool = False
	fold_to_donk_bet: bool = False
	raise_to_donk_bet: bool = False
	cbet_size_pct: float | None = None
	donk_bet_size_pct: float | None = None
	fold_to_cbet_raise: bool = False
	fold_to_donk_raise: bool = False


@dataclass
class TurnEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_preflop_raiser: bool
	hero_in_position: bool
	flop_action_sequence: ActionSequence
	turn_runout: Runout
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


@dataclass
class RiverEvent:
	played_on: date
	pot_type: PotType
	board_type: BoardType
	hero_in_position: bool
	flop_action_sequence: ActionSequence
	flop_rank_texture: FlopRankTexture
	turn_runout: Runout
	turn_action_sequence: ActionSequence
	river_runout: Runout
	river_action_sequence: ActionSequence
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
