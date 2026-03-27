import sqlite3

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_date_range
from app.db.queries import query_river_stats
from app.routers.params import (
    parse_bool_list, parse_board_type_list, parse_pot_type_list,
    parse_action_sequence_list, parse_flop_rank_texture_list,
    parse_runout_list,
)

router = APIRouter()


@router.get("")
def get_river(
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    flop_actions: list[str] | None = Query(default=None),
    flop_rank_textures: list[str] | None = Query(default=None),
    turn_runouts: list[str] | None = Query(default=None),
    turn_action_sequences: list[str] | None = Query(default=None),
    river_runouts: list[str] | None = Query(default=None),
    include_pool: bool = Query(default=False),
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    return query_river_stats(
        db, start=start, end=end,
        pot_types=parse_pot_type_list(pot_types),
        board_types=parse_board_type_list(board_types),
        hero_in_position=parse_bool_list(hero_in_position),
        flop_actions=parse_action_sequence_list(flop_actions),
        flop_rank_textures=parse_flop_rank_texture_list(flop_rank_textures),
        turn_runouts=parse_runout_list(turn_runouts),
        turn_action_sequences=parse_action_sequence_list(turn_action_sequences),
        river_runouts=parse_runout_list(river_runouts),
        include_pool=include_pool,
    )
