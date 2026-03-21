from fastapi import APIRouter, Depends, Query

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import RiverFilter, Rivers
from app.routers.params import (
    parse_bool_list, parse_board_type_list, parse_pot_type_list,
    parse_action_sequence_list, parse_flop_rank_texture_list,
    parse_runout_list, in_date_range,
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
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    f = RiverFilter(
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
        flop_actions=parse_action_sequence_list(flop_actions),
        flop_rank_textures=parse_flop_rank_texture_list(flop_rank_textures),
        turn_runouts=parse_runout_list(turn_runouts),
        turn_action_sequences=parse_action_sequence_list(turn_action_sequences),
        river_runouts=parse_runout_list(river_runouts),
    )
    filtered = [e for e in store.river_events if in_date_range(e.played_on, start, end)]
    rivers = Rivers()
    for event in filtered:
        rivers.add_event(event)
    return rivers.json(f)
