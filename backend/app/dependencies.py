import sqlite3
from datetime import date
from typing import Generator

from fastapi import Query, Request

from app.routers.params import parse_optional_date


def get_db(request: Request) -> Generator[sqlite3.Connection, None, None]:
    """Open a fresh read-only connection per request, closed when done."""
    conn = sqlite3.connect(request.app.state.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_date_range(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> tuple[date | None, date | None]:
    return parse_optional_date(start_date), parse_optional_date(end_date)
