import logging
import os
from datetime import date, datetime
from collections import Counter

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from models import CBetEvent, CBetFilter, CBets, FlopActionSequence, FlopRankTexture, LineEvents, LineFilter, RangeEvent, Ranges, RiverEvent, RiverFilter, RiverRunout, Rivers, TurnActionSequence, TurnEvent, TurnFilter, Turns, TurnRunout
from parser import parse_hand_dates, parse_histories
from playing_cards_lib.poker import BoardType, PotType

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base = os.path.dirname(__file__)
histories_dir = os.path.normpath(os.path.join(base, '..', 'hand_histories'))

paths = []
if os.path.isdir(histories_dir):
    for filename in os.listdir(histories_dir):
        path = os.path.join(histories_dir, filename)
        if not os.path.isfile(path):
            continue
        paths.append(path)

logger.info(f"Loading {len(paths)} hand history files...")
range_events, cbet_events, turn_events, river_events, line_events_list = parse_histories(paths)
hand_dates = parse_hand_dates(paths)
logger.info(f"Loaded {len(range_events)} range events, {len(cbet_events)} cbet events, {len(turn_events)} turn events, {len(river_events)} river events, {len(line_events_list)} line events")

line_events = LineEvents()
for le in line_events_list:
    line_events.add_event(le)


def parse_bool_list(values: list[str] | None) -> list[bool]:
    if values is None:
        return [True, False]
    parsed: list[bool] = []
    for value in values:
        for token in value.split(","):
            v = token.strip().lower()
            if v in ["true", "1", "t", "yes", "y"]:
                parsed.append(True)
            elif v in ["false", "0", "f", "no", "n"]:
                parsed.append(False)
    if not parsed:
        return [True, False]
    unique: list[bool] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_board_type_list(values: list[str] | None) -> list[BoardType]:
    if values is None:
        return list(BoardType)
    parsed: list[BoardType] = []
    mapping = {
        "MONOTONE": BoardType.MONOTONE,
        "TWO_TONE": BoardType.TWO_TONE,
        "2TONE": BoardType.TWO_TONE,
        "RAINBOW": BoardType.RAINBOW,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(BoardType)
    unique: list[BoardType] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_pot_type_list(values: list[str] | None) -> list[PotType]:
    if values is None:
        return list(PotType)
    parsed: list[PotType] = []
    mapping = {
        "SRP": PotType.SRP,
        "THREE_BET": PotType.THREE_BET,
        "3BET": PotType.THREE_BET,
        "FOUR_BET": PotType.FOUR_BET,
        "4BET": PotType.FOUR_BET,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(PotType)
    unique: list[PotType] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_turn_runout_list(values: list[str] | None) -> list[TurnRunout]:
    if values is None:
        return list(TurnRunout)
    parsed: list[TurnRunout] = []
    mapping = {
        "OVERCARD": TurnRunout.OVERCARD,
        "FLUSH_COMPLETING": TurnRunout.FLUSH_COMPLETING,
        "FLUSH": TurnRunout.FLUSH_COMPLETING,
        "PAIRED": TurnRunout.PAIRED,
        "OTHER": TurnRunout.OTHER,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(TurnRunout)
    unique: list[TurnRunout] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_flop_action_list(values: list[str] | None) -> list[FlopActionSequence]:
    if values is None:
        return list(FlopActionSequence)
    parsed: list[FlopActionSequence] = []
    mapping = {
        "XX": FlopActionSequence.XX,
        "XBC": FlopActionSequence.XBC,
        "XBRC": FlopActionSequence.XBRC,
        "BC": FlopActionSequence.BC,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(FlopActionSequence)
    unique: list[FlopActionSequence] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_river_runout_list(values: list[str] | None) -> list[RiverRunout]:
    if values is None:
        return list(RiverRunout)
    parsed: list[RiverRunout] = []
    mapping = {
        "OVERCARD": RiverRunout.OVERCARD,
        "FLUSH_COMPLETING": RiverRunout.FLUSH_COMPLETING,
        "FLUSH": RiverRunout.FLUSH_COMPLETING,
        "PAIRED": RiverRunout.PAIRED,
        "OTHER": RiverRunout.OTHER,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(RiverRunout)
    unique: list[RiverRunout] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_flop_rank_texture_list(values: list[str] | None) -> list[FlopRankTexture]:
    if values is None:
        return list(FlopRankTexture)
    parsed: list[FlopRankTexture] = []
    mapping = {
        "TRIPS": FlopRankTexture.TRIPS,
        "PAIRED": FlopRankTexture.PAIRED,
        "UNPAIRED": FlopRankTexture.UNPAIRED,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(FlopRankTexture)
    unique: list[FlopRankTexture] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_turn_action_sequence_list(values: list[str] | None) -> list[TurnActionSequence]:
    if values is None:
        return list(TurnActionSequence)
    parsed: list[TurnActionSequence] = []
    mapping = {
        "XX": TurnActionSequence.XX,
        "XBC": TurnActionSequence.XBC,
        "XBRC": TurnActionSequence.XBRC,
        "BC": TurnActionSequence.BC,
    }
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return list(TurnActionSequence)
    unique: list[TurnActionSequence] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


def parse_optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format") from e


def in_date_range(played_on: date, start_date: date | None, end_date: date | None) -> bool:
    if start_date is not None and played_on < start_date:
        return False
    if end_date is not None and played_on > end_date:
        return False
    return True


def filter_range_events(events: list[RangeEvent], start_date: date | None, end_date: date | None) -> list[RangeEvent]:
    return [event for event in events if in_date_range(event.played_on, start_date, end_date)]


def filter_cbet_events(events: list[CBetEvent], start_date: date | None, end_date: date | None) -> list[CBetEvent]:
    return [event for event in events if in_date_range(event.played_on, start_date, end_date)]


def aggregate_ranges(events: list[RangeEvent]) -> Ranges:
    ranges = Ranges()
    for event in events:
        ranges.add_hand(event.hand_key, event.position, event.action, event.pot_type, event.villain)
    return ranges


def aggregate_cbets(events: list[CBetEvent]) -> CBets:
    cbets = CBets()
    for event in events:
        cbets.add_event(event)
    return cbets


def filter_turn_events(events: list[TurnEvent], start_date: date | None, end_date: date | None) -> list[TurnEvent]:
    return [event for event in events if in_date_range(event.played_on, start_date, end_date)]


def aggregate_turns(events: list[TurnEvent]) -> Turns:
    turns = Turns()
    for event in events:
        turns.add_event(event)
    return turns


def filter_hand_dates(values: list[date], start_date: date | None, end_date: date | None) -> list[date]:
    return [value for value in values if in_date_range(value, start_date, end_date)]


def aggregate_daily_volume(values: list[date]) -> list[dict[str, int | str]]:
    counts = Counter(values)
    return [
        {"date": d.isoformat(), "count": counts[d]}
        for d in sorted(counts.keys())
    ]

@app.get("/")
def get_ranges(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    return aggregate_ranges(filter_range_events(range_events, start, end)).json()


@app.get("/cbets")
def get_cbets(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    bet_size_min: float | None = Query(default=None),
    bet_size_max: float | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    f = CBetFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
        bet_size_min=bet_size_min,
        bet_size_max=bet_size_max,
    )
    filtered = filter_cbet_events(cbet_events, start, end)
    return aggregate_cbets(filtered).json(f)


@app.get("/cbets/bet-sizes")
def get_cbet_bet_sizes(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    f = CBetFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
    )
    filtered = filter_cbet_events(cbet_events, start, end)
    return {"villain_bet_sizes": aggregate_cbets(filtered).bet_sizes(f)}


@app.get("/turn")
def get_turn(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    turn_runouts: list[str] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    f = TurnFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
        turn_runouts=parse_turn_runout_list(turn_runouts),
    )
    filtered = filter_turn_events(turn_events, start, end)
    return aggregate_turns(filtered).json(f)


@app.get("/hands/volume")
def get_hand_volume(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    return aggregate_daily_volume(filter_hand_dates(hand_dates, start, end))


def filter_river_events(events: list[RiverEvent], start_date: date | None, end_date: date | None) -> list[RiverEvent]:
    return [event for event in events if in_date_range(event.played_on, start_date, end_date)]


def aggregate_rivers(events: list[RiverEvent]) -> Rivers:
    rivers = Rivers()
    for event in events:
        rivers.add_event(event)
    return rivers


@app.get("/river")
def get_river(
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    flop_actions: list[str] | None = Query(default=None),
    flop_rank_textures: list[str] | None = Query(default=None),
    turn_runouts: list[str] | None = Query(default=None),
    turn_action_sequences: list[str] | None = Query(default=None),
    river_runouts: list[str] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    f = RiverFilter(
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
        flop_actions=parse_flop_action_list(flop_actions),
        flop_rank_textures=parse_flop_rank_texture_list(flop_rank_textures),
        turn_runouts=parse_turn_runout_list(turn_runouts),
        turn_action_sequences=parse_turn_action_sequence_list(turn_action_sequences),
        river_runouts=parse_river_runout_list(river_runouts),
    )
    filtered = filter_river_events(river_events, start, end)
    return aggregate_rivers(filtered).json(f)


@app.get("/line-analysis/flop")
def get_line_analysis_flop(
    hero_in_position: bool | None = Query(default=None),
    hero_preflop_raiser: bool | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
    actions: list[str] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    filtered_events = LineEvents()
    for e in line_events.events:
        if in_date_range(e.played_on, start, end):
            filtered_events.add_event(e)
    f = LineFilter(
        hero_in_position=hero_in_position,
        hero_preflop_raiser=hero_preflop_raiser,
        pot_types=parse_pot_type_list(pot_types),
        board_types=parse_board_type_list(board_types),
    )
    action_prefix = actions if actions else None
    return filtered_events.flop_spot_stats(f, action_prefix=action_prefix)
