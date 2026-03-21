import logging
import os
from dataclasses import dataclass, field
from datetime import date

from app.models import (
    CBetEvent, LineEvent, LineEvents, RangeEvent,
    RiverEvent, TurnEvent,
)
from app.parsers import parse_histories, parse_hand_dates

logger = logging.getLogger(__name__)


@dataclass
class EventStore:
    range_events: list[RangeEvent] = field(default_factory=list)
    cbet_events: list[CBetEvent] = field(default_factory=list)
    turn_events: list[TurnEvent] = field(default_factory=list)
    river_events: list[RiverEvent] = field(default_factory=list)
    line_events: LineEvents = field(default_factory=LineEvents)
    hand_dates: list[date] = field(default_factory=list)


def load_hand_histories(histories_dir: str | None = None) -> EventStore:
    if histories_dir is None:
        # __file__ = app/loader.py → up to app/ → up to backend/ → up to project root
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_dir = os.path.dirname(backend_dir)
        histories_dir = os.path.normpath(os.path.join(project_dir, 'hand_histories'))

    paths = []
    if os.path.isdir(histories_dir):
        for filename in sorted(os.listdir(histories_dir)):
            path = os.path.join(histories_dir, filename)
            if os.path.isfile(path):
                paths.append(path)

    logger.info(f"Loading {len(paths)} hand history files...")
    range_events, cbet_events, turn_events, river_events, line_events_list = parse_histories(paths)
    hand_dates = parse_hand_dates(paths)
    logger.info(
        f"Loaded {len(range_events)} range events, {len(cbet_events)} cbet events, "
        f"{len(turn_events)} turn events, {len(river_events)} river events, "
        f"{len(line_events_list)} line events"
    )

    store = EventStore(
        range_events=range_events,
        cbet_events=cbet_events,
        turn_events=turn_events,
        river_events=river_events,
        hand_dates=hand_dates,
    )
    for le in line_events_list:
        store.line_events.add_event(le)

    return store
