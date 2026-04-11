import sqlite3

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_date_range
from app.db.queries import query_hand_type_distribution
from app.routers.params import parse_board_type_list, parse_pot_type_list, parse_runout_list
from app.routers.line_analysis import _split_action_prefix

router = APIRouter()


@router.get("")
def get_hand_type_distribution(
	hero_in_position: bool | None = Query(default=None),
	hero_preflop_raiser: bool | None = Query(default=None),
	board_types: list[str] | None = Query(default=None),
	pot_types: list[str] | None = Query(default=None),
	turn_runouts: list[str] | None = Query(default=None),
	river_runouts: list[str] | None = Query(default=None),
	actions: list[str] | None = Query(default=None),
	include_pool: bool = Query(default=False),
	db: sqlite3.Connection = Depends(get_db),
	dates: tuple = Depends(get_date_range),
):
	start, end = dates
	flop_actions, turn_actions, river_actions = _split_action_prefix(actions)
	return query_hand_type_distribution(
		db, start=start, end=end,
		hero_in_position=hero_in_position,
		hero_preflop_raiser=hero_preflop_raiser,
		pot_types=parse_pot_type_list(pot_types),
		board_types=parse_board_type_list(board_types),
		turn_runouts=parse_runout_list(turn_runouts) if turn_runouts else None,
		river_runouts=parse_runout_list(river_runouts) if river_runouts else None,
		include_pool=include_pool,
		flop_actions=flop_actions, turn_actions=turn_actions, river_actions=river_actions,
	)
