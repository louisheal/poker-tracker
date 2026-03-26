import logging
import os
import pickle
from dataclasses import dataclass, field
from datetime import date

from app.models import (
    FlopEvent, LineEvent, LineEvents, RangeEvent,
    RiverEvent, TurnEvent,
)
from app.parsers import parse_file, FileParseResult

logger = logging.getLogger(__name__)

CACHE_DIR_NAME = ".cache"


def _cache_dir(histories_dir: str) -> str:
    path = os.path.join(histories_dir, CACHE_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _cache_path(histories_dir: str, filename: str) -> str:
    return os.path.join(_cache_dir(histories_dir), filename + ".pickle")


def _load_cached(histories_dir: str, filename: str, source_mtime: float) -> FileParseResult | None:
    cache = _cache_path(histories_dir, filename)
    if not os.path.exists(cache):
        return None
    try:
        cache_mtime = os.path.getmtime(cache)
        if cache_mtime < source_mtime:
            return None
        with open(cache, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.warning(f"Cache load failed for {filename}: {exc}")
        return None


def _save_cache(histories_dir: str, filename: str, result: FileParseResult):
    cache = _cache_path(histories_dir, filename)
    try:
        with open(cache, "wb") as f:
            pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as exc:
        logger.warning(f"Cache save failed for {filename}: {exc}")


@dataclass
class EventStore:
    range_events: list[RangeEvent] = field(default_factory=list)
    cbet_events: list[FlopEvent] = field(default_factory=list)
    turn_events: list[TurnEvent] = field(default_factory=list)
    river_events: list[RiverEvent] = field(default_factory=list)
    line_events: LineEvents = field(default_factory=LineEvents)
    hand_dates: list[date] = field(default_factory=list)


def load_hand_histories(histories_dir: str | None = None) -> EventStore:
    if histories_dir is None:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_dir = os.path.dirname(backend_dir)
        histories_dir = os.path.normpath(os.path.join(project_dir, 'hand_histories'))

    paths = []
    if os.path.isdir(histories_dir):
        for filename in sorted(os.listdir(histories_dir)):
            if filename == CACHE_DIR_NAME:
                continue
            path = os.path.join(histories_dir, filename)
            if os.path.isfile(path):
                paths.append(path)

    logger.info(f"Loading {len(paths)} hand history files...")

    combined = FileParseResult()
    cached_count = 0
    parsed_count = 0

    for path in paths:
        filename = os.path.basename(path)
        source_mtime = os.path.getmtime(path)

        result = _load_cached(histories_dir, filename, source_mtime)
        if result is not None:
            cached_count += 1
            logger.info(f"Loaded from cache: {filename}")
        else:
            logger.info(f"Parsing {filename}...")
            result = parse_file(path)
            _save_cache(histories_dir, filename, result)
            parsed_count += 1

        combined.merge(result)

    logger.info(
        f"Loaded {len(combined.range_events)} range, {len(combined.cbet_events)} cbet, "
        f"{len(combined.turn_events)} turn, {len(combined.river_events)} river, "
        f"{len(combined.line_events)} line events "
        f"({cached_count} cached, {parsed_count} parsed)"
    )

    store = EventStore(
        range_events=combined.range_events,
        cbet_events=combined.cbet_events,
        turn_events=combined.turn_events,
        river_events=combined.river_events,
        hand_dates=combined.hand_dates,
    )
    for le in combined.line_events:
        store.line_events.add_event(le)

    return store
