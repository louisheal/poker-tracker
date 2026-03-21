from collections import Counter

from fastapi import APIRouter, Depends

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.routers.params import in_date_range

router = APIRouter()


@router.get("")
def get_hand_volume(
    store: EventStore = Depends(get_store),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    filtered = [d for d in store.hand_dates if in_date_range(d, start, end)]
    counts = Counter(filtered)
    return [
        {"date": d.isoformat(), "count": counts[d]}
        for d in sorted(counts.keys())
    ]
