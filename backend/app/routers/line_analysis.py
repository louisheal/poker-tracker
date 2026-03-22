from fastapi import APIRouter, Depends, Query

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import LineEvents, LineFilter
from app.routers.params import parse_board_type_list, parse_pot_type_list, parse_runout_list, in_date_range

router = APIRouter()

TURN_MARKER = "TURN"


def _split_action_prefix(actions: list[str] | None) -> tuple[list[str] | None, list[str] | None]:
    if not actions:
        return None, None
    if TURN_MARKER in actions:
        idx = actions.index(TURN_MARKER)
        flop = actions[:idx] or None
        turn = actions[idx + 1:] or []
        return flop, turn
    return actions, None


@router.get("")
def get_line_analysis(
    hero_in_position: bool | None = Query(default=None),
    hero_preflop_raiser: bool | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    turn_runouts: list[str] | None = Query(default=None),
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
        turn_runouts=parse_runout_list(turn_runouts) if turn_runouts else None,
    )
    flop_prefix, turn_prefix = _split_action_prefix(actions)
    return filtered_events.spot_stats(f, flop_prefix=flop_prefix, turn_prefix=turn_prefix)
