import sqlite3

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_date_range
from app.db.queries import query_turn_stats
from app.routers.params import (
    parse_bool_list, parse_board_type_list, parse_pot_type_list,
    parse_runout_list,
)

router = APIRouter()


@router.get("")
def get_turn(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    turn_runouts: list[str] | None = Query(default=None),
    include_pool: bool = Query(default=False),
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    return query_turn_stats(
        db, start=start, end=end,
        pot_types=parse_pot_type_list(pot_types),
        board_types=parse_board_type_list(board_types),
        hero_in_position=parse_bool_list(hero_in_position),
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        turn_runouts=parse_runout_list(turn_runouts),
        include_pool=include_pool,
    )
