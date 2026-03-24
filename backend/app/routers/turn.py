from fastapi import APIRouter, Depends, Query

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import TurnFilter, Turns
from app.routers.params import (
    parse_bool_list, parse_board_type_list, parse_pot_type_list,
    parse_runout_list, in_date_range,
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
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    f = TurnFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
        turn_runouts=parse_runout_list(turn_runouts),
        include_pool=include_pool,
    )
    filtered = [e for e in store.turn_events if in_date_range(e.played_on, start, end)]
    turns = Turns()
    for event in filtered:
        turns.add_event(event)
    return turns.json(f)
