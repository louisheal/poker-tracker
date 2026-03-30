"""GTO preflop ranges and range filtering utilities.

Provides static opening/defending ranges per position and pot type,
plus functions to split a range into raise/call/fold sub-ranges
based on predicted villain response frequencies.
"""

from __future__ import annotations

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards
from app.models.enums import MadeHandType, FlushDrawType, StraightDrawType
from app.parsers.hand_types import classify_made_hand, classify_flush_draw, classify_straight_draw
from app.parsers.equity import get_equity, HandTriple

RANKS = list(Rank)

GTO_WEIGHT = 0.7
OBSERVED_WEIGHT = 0.3

# Standard 6-max GTO opening ranges (frequencies 0.0-1.0).
# Keys: (position, pot_type) -> dict[hand_key, frequency]
# These are approximate RFI (raise first in) / 3-bet / 4-bet frequencies
# derived from common GTO solutions.

_LJ_OPEN = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0, "88": 0.8,
    "77": 0.5, "66": 0.3,
    "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 0.5, "A5s": 0.7, "A4s": 0.5,
    "KQs": 1.0, "KJs": 1.0, "KTs": 0.8,
    "QJs": 1.0, "QTs": 0.7,
    "JTs": 1.0, "J9s": 0.3,
    "T9s": 0.8, "98s": 0.5, "87s": 0.3,
    "AKo": 1.0, "AQo": 1.0, "AJo": 0.8, "ATo": 0.3,
    "KQo": 0.7, "KJo": 0.3,
}

_HJ_OPEN = {
    **_LJ_OPEN,
    "88": 1.0, "77": 0.8, "66": 0.5, "55": 0.3,
    "A9s": 0.8, "A8s": 0.5, "A5s": 1.0, "A4s": 0.8, "A3s": 0.5,
    "KTs": 1.0, "K9s": 0.5,
    "QTs": 1.0, "Q9s": 0.3,
    "J9s": 0.7, "T9s": 1.0, "98s": 0.8, "87s": 0.5, "76s": 0.3,
    "AJo": 1.0, "ATo": 0.7,
    "KQo": 1.0, "KJo": 0.5, "KTo": 0.3,
    "QJo": 0.3,
}

_CO_OPEN = {
    **_HJ_OPEN,
    "77": 1.0, "66": 0.8, "55": 0.7, "44": 0.5, "33": 0.3, "22": 0.3,
    "A8s": 0.8, "A7s": 0.7, "A6s": 0.7, "A3s": 0.8, "A2s": 0.5,
    "K9s": 0.8, "K8s": 0.3,
    "Q9s": 0.7, "Q8s": 0.3,
    "J9s": 1.0, "J8s": 0.3,
    "T8s": 0.5, "97s": 0.5, "87s": 0.8, "76s": 0.7, "65s": 0.5,
    "ATo": 1.0, "A9o": 0.3,
    "KJo": 0.8, "KTo": 0.5,
    "QJo": 0.5, "QTo": 0.3,
    "JTo": 0.3,
}

_BTN_OPEN = {
    **_CO_OPEN,
    "55": 1.0, "44": 1.0, "33": 0.8, "22": 0.7,
    "A7s": 1.0, "A6s": 1.0, "A2s": 1.0,
    "K8s": 0.7, "K7s": 0.5, "K6s": 0.3,
    "Q8s": 0.7, "Q7s": 0.3,
    "J8s": 0.7, "T8s": 0.8, "97s": 0.8, "86s": 0.5, "75s": 0.5, "65s": 0.8, "54s": 0.5,
    "A9o": 0.8, "A8o": 0.3, "A7o": 0.3,
    "KTo": 0.8, "K9o": 0.3,
    "QTo": 0.7, "Q9o": 0.3,
    "JTo": 0.7, "J9o": 0.3,
    "T9o": 0.3,
}

_SB_OPEN = {
    **_CO_OPEN,
    "33": 0.5, "22": 0.5,
    "A2s": 0.8,
    "K8s": 0.5, "K7s": 0.3,
    "Q8s": 0.5,
    "J8s": 0.5, "T8s": 0.7, "97s": 0.7, "86s": 0.3, "76s": 0.8, "65s": 0.7, "54s": 0.3,
    "A9o": 0.5,
    "KTo": 0.7,
    "QJo": 0.7, "QTo": 0.5,
    "JTo": 0.5,
}

# 3-bet ranges (vs open from the listed position)
_THREE_BET_BASE = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 0.8, "TT": 0.5,
    "AKs": 1.0, "AQs": 0.8, "AJs": 0.5, "A5s": 0.5, "A4s": 0.3,
    "KQs": 0.5,
    "AKo": 1.0, "AQo": 0.5,
}

# 4-bet ranges
_FOUR_BET_BASE = {
    "AA": 1.0, "KK": 1.0, "QQ": 0.8, "JJ": 0.3,
    "AKs": 1.0, "AQs": 0.3, "A5s": 0.3,
    "AKo": 0.8,
}


def _build_gto_ranges() -> dict[tuple[str, str], dict[str, float]]:
    """Build the full GTO_RANGES lookup table."""
    opens = {
        "LJ": _LJ_OPEN, "HJ": _HJ_OPEN, "CO": _CO_OPEN,
        "BTN": _BTN_OPEN, "SB": _SB_OPEN,
    }

    ranges: dict[tuple[str, str], dict[str, float]] = {}

    # SRP ranges = opening ranges per position
    for pos, r in opens.items():
        ranges[(pos, "SRP")] = dict(r)

    # 3-bet ranges per position (slightly wider from later positions)
    for pos in ("LJ", "HJ", "CO", "BTN", "SB"):
        base = dict(_THREE_BET_BASE)
        ranges[(pos, "THREE_BET")] = base

    # 4-bet ranges
    for pos in ("LJ", "HJ", "CO", "BTN", "SB"):
        base = dict(_FOUR_BET_BASE)
        ranges[(pos, "FOUR_BET")] = base

    # BB defense ranges (calling range vs open)
    bb_defend = {
        "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
        "88": 1.0, "77": 1.0, "66": 0.8, "55": 0.7, "44": 0.5, "33": 0.3, "22": 0.3,
        "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 1.0, "A8s": 0.8,
        "A7s": 0.8, "A6s": 0.7, "A5s": 1.0, "A4s": 0.8, "A3s": 0.7, "A2s": 0.5,
        "KQs": 1.0, "KJs": 1.0, "KTs": 1.0, "K9s": 0.8, "K8s": 0.5, "K7s": 0.3,
        "QJs": 1.0, "QTs": 1.0, "Q9s": 0.8, "Q8s": 0.3,
        "JTs": 1.0, "J9s": 0.8, "J8s": 0.3,
        "T9s": 1.0, "T8s": 0.7, "98s": 0.8, "97s": 0.5,
        "87s": 0.8, "86s": 0.3, "76s": 0.7, "75s": 0.3, "65s": 0.7, "54s": 0.5,
        "AKo": 1.0, "AQo": 1.0, "AJo": 0.8, "ATo": 0.7, "A9o": 0.3,
        "KQo": 0.8, "KJo": 0.5, "KTo": 0.3,
        "QJo": 0.5, "QTo": 0.3,
        "JTo": 0.3,
    }
    for pot_type in ("SRP", "THREE_BET", "FOUR_BET"):
        ranges[("BB", pot_type)] = dict(bb_defend)

    return ranges


GTO_RANGES = _build_gto_ranges()


def get_starting_range(
    position: str,
    pot_type: str,
    observed_freqs: dict[str, float] | None = None,
) -> dict[str, float]:
    """Get a starting range for a position and pot type.

    If observed_freqs is provided, blends GTO with observed frequencies.
    """
    gto = GTO_RANGES.get((position, pot_type), {})
    if observed_freqs is None:
        return dict(gto)

    blended: dict[str, float] = {}
    all_keys = set(gto) | set(observed_freqs)
    for key in all_keys:
        g = gto.get(key, 0.0)
        o = observed_freqs.get(key, 0.0)
        blended[key] = GTO_WEIGHT * g + OBSERVED_WEIGHT * o
    return blended


def _hand_key_to_combos(hand_key: str) -> list[tuple[Card, Card]]:
    """Expand a hand key (e.g. 'AKs', 'QQ', 'T9o') into specific card combos."""
    if len(hand_key) == 2:
        # Pair: e.g. "AA"
        rank = Rank(hand_key[0])
        suits = list(Suit)
        combos = []
        for i in range(len(suits)):
            for j in range(i + 1, len(suits)):
                combos.append((Card(rank, suits[i]), Card(rank, suits[j])))
        return combos

    rank1 = Rank(hand_key[0])
    rank2 = Rank(hand_key[1])
    suffix = hand_key[2] if len(hand_key) > 2 else ""
    suits = list(Suit)

    if suffix == "s":
        return [(Card(rank1, s), Card(rank2, s)) for s in suits]
    else:
        return [
            (Card(rank1, s1), Card(rank2, s2))
            for s1 in suits for s2 in suits
            if s1 != s2
        ]


def _cards_conflict(combo: tuple[Card, Card], board: list[Card]) -> bool:
    """Check if a combo shares any card with the board."""
    for card in combo:
        for bc in board:
            if card.rank == bc.rank and card.suit == bc.suit:
                return True
    return False


def _classify_hand(
    hole: tuple[Card, Card],
    board: list[Card],
) -> HandTriple:
    """Classify a hand into the (MadeHand, FlushDraw, StraightDraw) triple."""
    hc = HoleCards(hole[0], hole[1])
    made = classify_made_hand(hc, board)
    fd = classify_flush_draw(hc, board)
    sd = classify_straight_draw(hc, board)
    return (made, fd, sd)


def compute_hand_equity(
    hero_triple: HandTriple,
    villain_range: dict[str, float],
    board: list[Card],
    street: str,
) -> float:
    """Weighted average equity of a hero hand triple vs a villain range."""
    total_weight = 0.0
    weighted_equity = 0.0

    for hand_key, freq in villain_range.items():
        if freq <= 0:
            continue
        combos = _hand_key_to_combos(hand_key)
        for combo in combos:
            if _cards_conflict(combo, board):
                continue
            villain_triple = _classify_hand(combo, board)
            eq = get_equity(hero_triple, villain_triple, street)
            weighted_equity += eq * freq
            total_weight += freq
            break  # Use first valid combo as representative

    return weighted_equity / total_weight if total_weight > 0 else 0.5


def filter_range_by_equity(
    range_: dict[str, float],
    board: list[Card],
    street: str,
    raise_pct: float,
    call_pct: float,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Split a range into raise/call/fold sub-ranges by equity ranking.

    Sorts hands by equity vs the full range, then assigns:
      - Top raise_pct to raising range
      - Next call_pct to calling range
      - Remainder to folding range

    Returns (raising_range, calling_range, folding_range).
    """
    # Compute equity for each hand in range
    equities: list[tuple[str, float, float]] = []  # (hand_key, freq, equity)

    for hand_key, freq in range_.items():
        if freq <= 0:
            continue
        combos = _hand_key_to_combos(hand_key)
        valid_combo = None
        for combo in combos:
            if not _cards_conflict(combo, board):
                valid_combo = combo
                break
        if valid_combo is None:
            continue

        triple = _classify_hand(valid_combo, board)
        eq = compute_hand_equity(triple, range_, board, street)
        equities.append((hand_key, freq, eq))

    # Sort by equity descending (strongest hands first)
    equities.sort(key=lambda x: x[2], reverse=True)

    total_combos = sum(freq for _, freq, _ in equities)
    if total_combos <= 0:
        return {}, {}, {}

    raising_range: dict[str, float] = {}
    calling_range: dict[str, float] = {}
    folding_range: dict[str, float] = {}

    cumulative = 0.0
    raise_threshold = raise_pct / 100.0
    call_threshold = (raise_pct + call_pct) / 100.0

    for hand_key, freq, _ in equities:
        position = cumulative / total_combos
        if position < raise_threshold:
            raising_range[hand_key] = freq
        elif position < call_threshold:
            calling_range[hand_key] = freq
        else:
            folding_range[hand_key] = freq
        cumulative += freq

    return raising_range, calling_range, folding_range
