from fastapi import APIRouter, Depends

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import Ranges
from app.routers.params import in_date_range

router = APIRouter()


@router.get("/")
def get_ranges(
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    filtered = [e for e in store.range_events if in_date_range(e.played_on, start, end)]
    ranges = Ranges()
    for event in filtered:
        ranges.add_hand(event.hand_key, event.position, event.action, event.pot_type, event.villain)
    return ranges.json()
