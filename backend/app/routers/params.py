from datetime import date, datetime
from typing import TypeVar

from fastapi import HTTPException

from app.models import ActionSequence, Runout, FlopRankTexture, BoardType, PotType

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
BOARD_TYPE_MAP: dict[str, BoardType] = {
    "MONOTONE": BoardType.MONOTONE,
    "TWO_TONE": BoardType.TWO_TONE,
    "2TONE": BoardType.TWO_TONE,
    "RAINBOW": BoardType.RAINBOW,
}

POT_TYPE_MAP: dict[str, PotType] = {
    "SRP": PotType.SRP,
    "srp": PotType.SRP,
    "THREE_BET": PotType.THREE_BET,
    "threeBet": PotType.THREE_BET,
    "3BET": PotType.THREE_BET,
    "FOUR_BET": PotType.FOUR_BET,
    "fourBet": PotType.FOUR_BET,
    "4BET": PotType.FOUR_BET,
}

RUNOUT_MAP: dict[str, Runout] = {
    "OVERCARD": Runout.OVERCARD,
    "FLUSH_COMPLETING": Runout.FLUSH_COMPLETING,
    "FLUSH": Runout.FLUSH_COMPLETING,
    "PAIRED": Runout.PAIRED,
    "OTHER": Runout.OTHER,
}

ACTION_SEQUENCE_MAP: dict[str, ActionSequence] = {
    "XX": ActionSequence.XX,
    "XBC": ActionSequence.XBC,
    "XBRC": ActionSequence.XBRC,
    "BC": ActionSequence.BC,
}

FLOP_RANK_MAP: dict[str, FlopRankTexture] = {
    "TRIPS": FlopRankTexture.TRIPS,
    "PAIRED": FlopRankTexture.PAIRED,
    "UNPAIRED": FlopRankTexture.UNPAIRED,
}


def parse_board_type_list(values: list[str] | None) -> list[BoardType]:
    return parse_enum_list(values, BOARD_TYPE_MAP, list(BoardType))


def parse_pot_type_list(values: list[str] | None) -> list[PotType]:
    return parse_enum_list(values, POT_TYPE_MAP, list(PotType))


def parse_runout_list(values: list[str] | None) -> list[Runout]:
    return parse_enum_list(values, RUNOUT_MAP, list(Runout))


def parse_action_sequence_list(values: list[str] | None) -> list[ActionSequence]:
    return parse_enum_list(values, ACTION_SEQUENCE_MAP, list(ActionSequence))


def parse_flop_rank_texture_list(values: list[str] | None) -> list[FlopRankTexture]:
    return parse_enum_list(values, FLOP_RANK_MAP, list(FlopRankTexture))


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
