"""AST node types for parsed poker hand histories."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from playing_cards_lib.core import Card
from playing_cards_lib.poker import HoleCards

from app.models.enums import (
	ActionSequence, Runout,
	FlopRankTexture, ShowdownType,
	BoardType, PotType,
)


class ActionType(Enum):
	FOLD = "fold"
	CHECK = "check"
	CALL = "call"
	BET = "bet"
	RAISE = "raise"


@dataclass
class Action:
	"""A single player action in any street."""
	player: str
	type: ActionType
	amount: float | None = None       # $ for bet/call; raise increment for raise
	raise_to: float | None = None     # "raises $X to $Y" — Y (total)
	is_hero: bool = False


@dataclass
class BlindPost:
	"""A blind posting."""
	player: str
	amount: float
	is_small: bool
	is_hero: bool = False


@dataclass
class Street:
	"""A post-flop street: community cards + actions."""
	cards: list[Card]
	actions: list[Action] = field(default_factory=list)


@dataclass
class HandAST:
	"""Complete structured representation of one hand history."""
	hand_id: str
	played_on: date
	button_seat: int
	players: list[tuple[str, int, float]]
	hero_hole_cards: HoleCards | None
	blinds: list[BlindPost]
	preflop: list[Action]
	flop: Street | None = None
	turn: Street | None = None
	river: Street | None = None
	hero_collected: float = 0.0
	collections: dict[str, float] = field(default_factory=dict)
	total_pot: float = 0.0
	uncalled_amount: float = 0.0
	uncalled_to: str | None = None
	hero_showed_won: bool | None = None  # True=won, False=lost, None=no show
	shown_cards: dict[str, HoleCards] = field(default_factory=dict)


@dataclass
class HandContext:
	"""Cached derived values computed once from a HandAST."""
	ast: HandAST
	hero_sees_flop: bool = False
	board_type: BoardType | None = None
	flop_rank_texture: FlopRankTexture | None = None
	hero_in_position: bool = False
	hero_preflop_raiser: bool = False
	pot_type: PotType = field(default=PotType.SRP)
	pot_at_flop_bb: float = 0.0
	hero_pnl_bb: float = 0.0
	hero_preflop_invested_bb: float = 0.0
	has_hero_pnl: bool = False
	flop_action_sequence: ActionSequence | None = None
	turn_runout: Runout | None = None
	turn_action_sequence: ActionSequence | None = None
	river_runout: Runout | None = None
	river_action_sequence: ActionSequence | None = None
	showdown_type: ShowdownType | None = None
	went_to_showdown: bool = False
	hero_won_showdown: bool = False
	pot_size_bb: float = 0.0
	perspective_player: str = "Hero"
