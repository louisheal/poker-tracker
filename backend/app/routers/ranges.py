import sqlite3

from fastapi import APIRouter, Depends

from app.dependencies import get_db, get_date_range
from app.db.queries import query_ranges
from app.models import Ranges

router = APIRouter()


@router.get("/")
def get_ranges(
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    rows = query_ranges(db, start=start, end=end)
    ranges = Ranges()
    for row in rows:
        ranges.add_hand(row["hand_key"], row["position"], row["action"], row["pot_type"], row["villain"])
    return ranges.json()
