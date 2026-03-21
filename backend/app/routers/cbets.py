from fastapi import APIRouter, Depends, Query

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import FlopFilter, Flops
from app.routers.params import parse_bool_list, parse_board_type_list, parse_pot_type_list, in_date_range

router = APIRouter()


@router.get("")
def get_cbets(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    bet_size_min: float | None = Query(default=None),
    bet_size_max: float | None = Query(default=None),
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    f = FlopFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
        bet_size_min=bet_size_min,
        bet_size_max=bet_size_max,
    )
    filtered = [e for e in store.cbet_events if in_date_range(e.played_on, start, end)]
    cbets = Flops()
    for event in filtered:
        cbets.add_event(event)
    return cbets.json(f)


@router.get("/bet-sizes")
def get_cbet_bet_sizes(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    f = FlopFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
    )
    filtered = [e for e in store.cbet_events if in_date_range(e.played_on, start, end)]
    cbets = Flops()
    for event in filtered:
        cbets.add_event(event)
    return {"villain_bet_sizes": cbets.bet_sizes(f)}
