from fastapi import APIRouter, Depends, Query

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import LineEvents, LineFilter
from app.routers.params import parse_board_type_list, parse_pot_type_list, in_date_range

router = APIRouter()


@router.get("")
def get_line_analysis_flop(
    hero_in_position: bool | None = Query(default=None),
    hero_preflop_raiser: bool | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    actions: list[str] | None = Query(default=None),
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    filtered_events = LineEvents()
    for e in store.line_events.events:
        if in_date_range(e.played_on, start, end):
            filtered_events.add_event(e)
    f = LineFilter(
        hero_in_position=hero_in_position,
        hero_preflop_raiser=hero_preflop_raiser,
        pot_types=parse_pot_type_list(pot_types),
        board_types=parse_board_type_list(board_types),
    )
    action_prefix = actions if actions else None
    return filtered_events.flop_spot_stats(f, action_prefix=action_prefix)
