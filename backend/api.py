import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from models import CBetFilter
from playing_cards_lib.poker import BoardType, PotType
from parser import parse_histories

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

ranges, cbets = parse_histories(paths)


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

@app.get("/")
def get_ranges():
    return ranges.json()


@app.get("/cbets")
def get_cbets(
    hero_preflop_raiser: list[str] | None = Query(default=None),
    hero_in_position: list[str] | None = Query(default=None),
    board_types: list[str] | None = Query(default=None),
    pot_types: list[str] | None = Query(default=None),
):
    f = CBetFilter(
        hero_preflop_raiser=parse_bool_list(hero_preflop_raiser),
        hero_in_position=parse_bool_list(hero_in_position),
        board_types=parse_board_type_list(board_types),
        pot_types=parse_pot_type_list(pot_types),
    )
    return cbets.json(f)
