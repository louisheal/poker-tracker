import sqlite3

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_date_range
from app.db.queries import query_flop_stats, query_flop_bet_sizes
from app.routers.params import parse_bool_list, parse_board_type_list, parse_pot_type_list

router = APIRouter()


@router.get("")
def get_flop(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    bet_size_min: float | None = Query(default=None),
    bet_size_max: float | None = Query(default=None),
    include_pool: bool = Query(default=False),
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    return query_flop_stats(
        db, start=start, end=end,
        pot_types=parse_pot_type_list(pot_types),
        board_types=parse_board_type_list(board_types),
        hero_in_position=parse_bool_list(hero_in_position),
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        bet_size_min=bet_size_min, bet_size_max=bet_size_max,
        include_pool=include_pool,
    )


@router.get("/bet-sizes")
def get_flop_bet_sizes(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    include_pool: bool = Query(default=False),
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    return {"villain_bet_sizes": query_flop_bet_sizes(
        db, start=start, end=end,
        pot_types=parse_pot_type_list(pot_types),
        board_types=parse_board_type_list(board_types),
        hero_in_position=parse_bool_list(hero_in_position),
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        include_pool=include_pool,
    )}
