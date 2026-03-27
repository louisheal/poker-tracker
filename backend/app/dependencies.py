import sqlite3
from datetime import date

from fastapi import Query, Request

from app.routers.params import parse_optional_date


def get_db(request: Request) -> sqlite3.Connection:
    """Open a fresh connection per request for thread-safe concurrent reads."""
    conn = sqlite3.connect(request.app.state.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_date_range(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> tuple[date | None, date | None]:
    return parse_optional_date(start_date), parse_optional_date(end_date)
