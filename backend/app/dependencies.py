from datetime import date

from fastapi import Query, Request

from app.loader import EventStore
from app.routers.params import parse_optional_date


def get_store(request: Request) -> EventStore:
    return request.app.state.store


def get_date_range(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> tuple[date | None, date | None]:
    return parse_optional_date(start_date), parse_optional_date(end_date)
