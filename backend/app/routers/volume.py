import sqlite3

from fastapi import APIRouter, Depends

from app.dependencies import get_db, get_date_range
from app.db.queries import query_hand_volume

router = APIRouter()


@router.get("")
def get_hand_volume(
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    return query_hand_volume(db, start=start, end=end)
