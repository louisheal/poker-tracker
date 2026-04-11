import sqlite3

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_date_range
from app.routers.params import parse_board_type_list, parse_pot_type_list, parse_runout_list
from app.services.street_stats import get_street_stats, build_base_key

router = APIRouter()


@router.get("/street-stats")
def get_street_stats_endpoint(
	flop_sequence: str = Query(default=""),
	turn_sequence: str | None = Query(default=None),
	river_sequence: str | None = Query(default=None),
	hero_ip: bool | None = Query(default=None),
	hero_pfr: bool | None = Query(default=None),
	board_types: list[str] | None = Query(default=None),
	pot_types: list[str] | None = Query(default=None),
	turn_runouts: list[str] | None = Query(default=None),
	river_runouts: list[str] | None = Query(default=None),
	include_pool: bool = Query(default=False),
	db: sqlite3.Connection = Depends(get_db),
	dates: tuple = Depends(get_date_range),
):
	base_key = build_base_key(flop_sequence, turn_sequence, river_sequence)
	start, end = dates

	parsed_board = parse_board_type_list(board_types) if board_types else None
	parsed_pot = parse_pot_type_list(pot_types) if pot_types else None
	parsed_turn_runout = parse_runout_list(turn_runouts) if turn_runouts else None
	parsed_river_runout = parse_runout_list(river_runouts) if river_runouts else None

	return get_street_stats(
		db, base_key,
		hero_ip=hero_ip,
		hero_pfr=hero_pfr,
		pot_types=parsed_pot,
		board_types=parsed_board,
		turn_runouts=parsed_turn_runout,
		river_runouts=parsed_river_runout,
		start=start,
		end=end,
		include_pool=include_pool,
	)
