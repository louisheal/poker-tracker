"""Shared data types for the solver package."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class TokenType(IntEnum):
    CARD = 0
    ACTION = 1
    STREET_MARKER = 2


@dataclass
class Token:
    token_type: TokenType
    rank: int = 0       # 0-12 for cards
    suit: int = 0       # 0-3 for cards
    action: int = 0     # 0-4 for actions (F/X/C/B/R)
    bet_size_pct: float = 0.0  # pct of pot for bet/raise actions
