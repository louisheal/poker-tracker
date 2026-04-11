import sqlite3

from fastapi import APIRouter, Depends

from playing_cards_lib.poker import PokerPosition

from app.dependencies import get_db, get_date_range
from app.db.queries import query_ranges
from app.models import Ranges
from app.models.enums import PotType

router = APIRouter()

_POS_MAP = {str(p.value): p for p in PokerPosition}
_POT_MAP = {p.value: p for p in PotType}


@router.get("/")
def get_ranges(
    db: sqlite3.Connection = Depends(get_db),
    dates: tuple = Depends(get_date_range),
):
    start, end = dates
    rows = query_ranges(db, start=start, end=end)
    ranges = Ranges()
    for row in rows:
        position = _POS_MAP.get(row["position"])
        pot_type = _POT_MAP.get(row["pot_type"])
        villain = _POS_MAP.get(row["villain"]) if row["villain"] else None
        if position is None or pot_type is None:
            continue
        ranges.add_hand(row["hand_key"], position, row["action"], pot_type, villain)
    return ranges.json()
