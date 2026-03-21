from datetime import date, datetime
from typing import TypeVar

from fastapi import HTTPException

from playing_cards_lib.poker import BoardType, PotType

from app.models import (
    FlopActionSequence, FlopRankTexture,
    RiverRunout, TurnActionSequence, TurnRunout,
)

T = TypeVar("T")


def parse_enum_list(
    values: list[str] | None,
    mapping: dict[str, T],
    default: list[T] | None = None,
) -> list[T]:
    """Generic parser for enum query params with comma-split support."""
    if default is None:
        default = list(mapping.values())
    if values is None:
        return default
    parsed: list[T] = []
    for value in values:
        for token in value.split(","):
            t = token.strip().upper()
            if t in mapping:
                parsed.append(mapping[t])
    if not parsed:
        return default
    seen = set()
    unique: list[T] = []
    for v in parsed:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def parse_bool_list(values: list[str] | None) -> list[bool]:
    if values is None:
        return [True, False]
    parsed: list[bool] = []
    for value in values:
        for token in value.split(","):
            v = token.strip().lower()
            if v in ("true", "1", "t", "yes", "y"):
                parsed.append(True)
            elif v in ("false", "0", "f", "no", "n"):
                parsed.append(False)
    if not parsed:
        return [True, False]
    unique: list[bool] = []
    for value in parsed:
        if value not in unique:
            unique.append(value)
    return unique


# Pre-built mappings
BOARD_TYPE_MAP = {
    "MONOTONE": BoardType.MONOTONE,
    "TWO_TONE": BoardType.TWO_TONE,
    "2TONE": BoardType.TWO_TONE,
    "RAINBOW": BoardType.RAINBOW,
}

POT_TYPE_MAP = {
    "SRP": PotType.SRP,
    "THREE_BET": PotType.THREE_BET,
    "3BET": PotType.THREE_BET,
    "FOUR_BET": PotType.FOUR_BET,
    "4BET": PotType.FOUR_BET,
}

TURN_RUNOUT_MAP = {
    "OVERCARD": TurnRunout.OVERCARD,
    "FLUSH_COMPLETING": TurnRunout.FLUSH_COMPLETING,
    "FLUSH": TurnRunout.FLUSH_COMPLETING,
    "PAIRED": TurnRunout.PAIRED,
    "OTHER": TurnRunout.OTHER,
}

FLOP_ACTION_MAP = {
    "XX": FlopActionSequence.XX,
    "XBC": FlopActionSequence.XBC,
    "XBRC": FlopActionSequence.XBRC,
    "BC": FlopActionSequence.BC,
}

RIVER_RUNOUT_MAP = {
    "OVERCARD": RiverRunout.OVERCARD,
    "FLUSH_COMPLETING": RiverRunout.FLUSH_COMPLETING,
    "FLUSH": RiverRunout.FLUSH_COMPLETING,
    "PAIRED": RiverRunout.PAIRED,
    "OTHER": RiverRunout.OTHER,
}

FLOP_RANK_MAP = {
    "TRIPS": FlopRankTexture.TRIPS,
    "PAIRED": FlopRankTexture.PAIRED,
    "UNPAIRED": FlopRankTexture.UNPAIRED,
}

TURN_ACTION_MAP = {
    "XX": TurnActionSequence.XX,
    "XBC": TurnActionSequence.XBC,
    "XBRC": TurnActionSequence.XBRC,
    "BC": TurnActionSequence.BC,
}


def parse_board_type_list(values):
    return parse_enum_list(values, BOARD_TYPE_MAP, list(BoardType))


def parse_pot_type_list(values):
    return parse_enum_list(values, POT_TYPE_MAP, list(PotType))


def parse_turn_runout_list(values):
    return parse_enum_list(values, TURN_RUNOUT_MAP, list(TurnRunout))


def parse_flop_action_list(values):
    return parse_enum_list(values, FLOP_ACTION_MAP, list(FlopActionSequence))


def parse_river_runout_list(values):
    return parse_enum_list(values, RIVER_RUNOUT_MAP, list(RiverRunout))


def parse_flop_rank_texture_list(values):
    return parse_enum_list(values, FLOP_RANK_MAP, list(FlopRankTexture))


def parse_turn_action_sequence_list(values):
    return parse_enum_list(values, TURN_ACTION_MAP, list(TurnActionSequence))


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
