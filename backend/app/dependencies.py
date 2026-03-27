import sqlite3
from datetime import date

from fastapi import Query, Request

from app.routers.params import parse_optional_date


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


def get_date_range(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> tuple[date | None, date | None]:
    return parse_optional_date(start_date), parse_optional_date(end_date)
