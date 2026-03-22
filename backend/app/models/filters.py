from playing_cards_lib.poker import PokerPosition

from .enums import ActionSequence, Runout, FlopRankTexture, BoardType, PotType


class FlopFilter:
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


class LineFilter:
	def __init__(
		self,
		hero_in_position: bool | None = None,
		hero_preflop_raiser: bool | None = None,
		pot_types: list[PotType] | None = None,
		board_types: list[BoardType] | None = None,
		turn_runouts: list[Runout] | None = None,
		river_runouts: list[Runout] | None = None,
	):
		self.hero_in_position = hero_in_position
		self.hero_preflop_raiser = hero_preflop_raiser
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.turn_runouts = turn_runouts
		self.river_runouts = river_runouts


class TurnFilter:
	def __init__(
		self,
		pot_types: list[PotType] | None = None,
		board_types: list[BoardType] | None = None,
		hero_preflop_raiser: list[bool] | None = None,
		hero_in_position: list[bool] | None = None,
		turn_runouts: list[Runout] | None = None,
	):
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.hero_preflop_raiser = hero_preflop_raiser if hero_preflop_raiser is not None else [True, False]
		self.hero_in_position = hero_in_position if hero_in_position is not None else [True, False]
		self.turn_runouts = turn_runouts if turn_runouts is not None else list(Runout)


class RiverFilter:
	def __init__(
		self,
		pot_types: list[PotType] | None = None,
		board_types: list[BoardType] | None = None,
		hero_in_position: list[bool] | None = None,
		flop_actions: list[ActionSequence] | None = None,
		flop_rank_textures: list[FlopRankTexture] | None = None,
		turn_runouts: list[Runout] | None = None,
		turn_action_sequences: list[ActionSequence] | None = None,
		river_runouts: list[Runout] | None = None,
	):
		self.pot_types = pot_types if pot_types is not None else list(PotType)
		self.board_types = board_types if board_types is not None else list(BoardType)
		self.hero_in_position = hero_in_position if hero_in_position is not None else [True, False]
		self.flop_actions = flop_actions if flop_actions is not None else list(ActionSequence)
		self.flop_rank_textures = flop_rank_textures if flop_rank_textures is not None else list(FlopRankTexture)
		self.turn_runouts = turn_runouts if turn_runouts is not None else list(Runout)
		self.turn_action_sequences = turn_action_sequences if turn_action_sequences is not None else list(ActionSequence)
		self.river_runouts = river_runouts if river_runouts is not None else list(Runout)
