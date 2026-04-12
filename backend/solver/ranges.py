"""GTO preflop ranges and range filtering utilities.

Provides static opening/defending ranges per position and pot type,
plus functions to split a range into raise/call/fold sub-ranges
based on predicted villain response frequencies.

Range types:
  OPEN       - RFI (raise first in) per position
  CALL_OPEN  - Flat call vs an open (keyed by vs_position)
  THREE_BET  - 3-bet vs an open (keyed by vs_position)
  FOUR_BET   - 4-bet vs a 3-bet
"""

from __future__ import annotations

import itertools

import eval7

from playing_cards_lib.core import Card, Rank, Suit

RANKS = list(Rank)

# Pre-built eval7 Card lookup to avoid repeated string construction
_ALL_EVAL7_CARDS: dict[tuple[str, str], eval7.Card] = {
    (r.value, s.value): eval7.Card(f"{r.value}{s.value.lower()}")
    for r in Rank for s in Suit
}

# Full deck of eval7 cards for runout enumeration
_EVAL7_DECK: list[eval7.Card] = list(_ALL_EVAL7_CARDS.values())


def _card_to_eval7(card: Card) -> eval7.Card:
    """Convert a playing_cards_lib Card to an eval7 Card."""
    return _ALL_EVAL7_CARDS[(card.rank.value, card.suit.value)]


def _combos_conflict(a: tuple[Card, Card], b: tuple[Card, Card]) -> bool:
    """Check if two combos share any card."""
    for ca in a:
        for cb in b:
            if ca.rank == cb.rank and ca.suit == cb.suit:
                return True
    return False


# Canonical Rank/Suit ordering for normalizing combo tuples
_RANK_ORDER = {r: i for i, r in enumerate(Rank)}
_SUIT_ORDER = {s: i for i, s in enumerate(Suit)}


def _normalize_combo(combo: tuple[Card, Card]) -> tuple[Card, Card]:
    """Normalize combo tuple ordering for consistent dict lookups.

    ALL_COMBOS uses (lower_rank, higher_rank) ordering, but
    _hand_key_to_combos uses (higher_rank, lower_rank). This ensures
    both map to the same key.
    """
    a, b = combo
    ka = (_RANK_ORDER[a.rank], _SUIT_ORDER[a.suit])
    kb = (_RANK_ORDER[b.rank], _SUIT_ORDER[b.suit])
    if ka > kb:
        return (b, a)
    return combo

GTO_WEIGHT = 0.7
OBSERVED_WEIGHT = 0.3

# ---------------------------------------------------------------------------
# Opening ranges (RFI) per position
# ---------------------------------------------------------------------------

_LJ_OPEN = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0, "88": 1.0,
    "77": 1.0, "66": 1.0,
    "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 1.0, "A5s": 1.0, "A4s": 1.0,
    "KQs": 1.0, "KJs": 1.0, "KTs": 1.0,
    "QJs": 1.0, "QTs": 1.0,
    "JTs": 1.0, "J9s": 1.0,
    "T9s": 1.0, "98s": 1.0, "87s": 1.0,
    "AKo": 1.0, "AQo": 1.0, "AJo": 1.0, "ATo": 1.0,
    "KQo": 1.0, "KJo": 1.0,
}

_HJ_OPEN = {
    **_LJ_OPEN,
    "88": 1.0, "77": 1.0, "66": 1.0, "55": 1.0,
    "A9s": 1.0, "A8s": 1.0, "A5s": 1.0, "A4s": 1.0, "A3s": 1.0,
    "KTs": 1.0, "K9s": 1.0,
    "QTs": 1.0, "Q9s": 1.0,
    "J9s": 1.0, "T9s": 1.0, "98s": 1.0, "87s": 1.0, "76s": 1.0,
    "AJo": 1.0, "ATo": 1.0,
    "KQo": 1.0, "KJo": 1.0, "KTo": 1.0,
    "QJo": 1.0,
}

_CO_OPEN = {
    **_HJ_OPEN,
    "77": 1.0, "66": 1.0, "55": 1.0, "44": 1.0, "33": 1.0, "22": 1.0,
    "A8s": 1.0, "A7s": 1.0, "A6s": 1.0, "A3s": 1.0, "A2s": 1.0,
    "K9s": 1.0, "K8s": 1.0,
    "Q9s": 1.0, "Q8s": 1.0,
    "J9s": 1.0, "J8s": 1.0,
    "T8s": 1.0, "97s": 1.0, "87s": 1.0, "76s": 1.0, "65s": 1.0,
    "ATo": 1.0, "A9o": 1.0,
    "KJo": 1.0, "KTo": 1.0,
    "QJo": 1.0, "QTo": 1.0,
    "JTo": 1.0,
}

_BTN_OPEN = {
    **_CO_OPEN,
    "55": 1.0, "44": 1.0, "33": 1.0, "22": 1.0,
    "A7s": 1.0, "A6s": 1.0, "A2s": 1.0,
    "K8s": 1.0, "K7s": 1.0, "K6s": 1.0,
    "Q8s": 1.0, "Q7s": 1.0,
    "J8s": 1.0, "T8s": 1.0, "97s": 1.0, "86s": 1.0, "75s": 1.0, "65s": 1.0, "54s": 1.0,
    "A9o": 1.0, "A8o": 1.0, "A7o": 1.0,
    "KTo": 1.0, "K9o": 1.0,
    "QTo": 1.0, "Q9o": 1.0,
    "JTo": 1.0, "J9o": 1.0,
    "T9o": 1.0,
}

_SB_OPEN = {
    **_CO_OPEN,
    "33": 1.0, "22": 1.0,
    "A2s": 1.0,
    "K8s": 1.0, "K7s": 1.0,
    "Q8s": 1.0,
    "J8s": 1.0, "T8s": 1.0, "97s": 1.0, "86s": 1.0, "76s": 1.0, "65s": 1.0, "54s": 1.0,
    "A9o": 1.0,
    "KTo": 1.0,
    "QJo": 1.0, "QTo": 1.0,
    "JTo": 1.0,
}

OPEN_RANGES: dict[str, dict[str, float]] = {
    "LJ": _LJ_OPEN, "HJ": _HJ_OPEN, "CO": _CO_OPEN,
    "BTN": _BTN_OPEN, "SB": _SB_OPEN,
}

# ---------------------------------------------------------------------------
# BB 3-bet ranges vs each opener (premiums + polarised bluffs)
# Wider vs later positions, tighter vs early positions
# ---------------------------------------------------------------------------

_BB_3BET_VS_LJ = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0,
    "AKs": 1.0, "AQs": 1.0, "A5s": 1.0, "A4s": 1.0,
    "AKo": 1.0,
}

_BB_3BET_VS_HJ = {
    **_BB_3BET_VS_LJ,
    "JJ": 1.0, "TT": 1.0,
    "AQs": 1.0, "A4s": 1.0, "A3s": 1.0,
    "KQs": 1.0,
    "AQo": 1.0,
}

_BB_3BET_VS_CO = {
    **_BB_3BET_VS_HJ,
    "JJ": 1.0, "TT": 1.0,
    "AQs": 1.0, "AJs": 1.0, "A3s": 1.0, "A2s": 1.0,
    "KQs": 1.0,
    "AQo": 1.0,
}

_BB_3BET_VS_BTN = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
    "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0,
    "A5s": 1.0, "A4s": 1.0, "A3s": 1.0, "A2s": 1.0,
    "KQs": 1.0, "KJs": 1.0,
    "QJs": 1.0,
    "AKo": 1.0, "AQo": 1.0, "AJo": 1.0,
    "KQo": 1.0,
}

_BB_3BET_VS_SB = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
    "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0,
    "A5s": 1.0, "A4s": 1.0, "A3s": 1.0, "A2s": 1.0,
    "KQs": 1.0, "KJs": 1.0, "KTs": 1.0,
    "QJs": 1.0, "QTs": 1.0,
    "JTs": 1.0,
    "AKo": 1.0, "AQo": 1.0, "AJo": 1.0,
    "KQo": 1.0,
}

BB_3BET_RANGES: dict[str, dict[str, float]] = {
    "LJ": _BB_3BET_VS_LJ, "HJ": _BB_3BET_VS_HJ, "CO": _BB_3BET_VS_CO,
    "BTN": _BB_3BET_VS_BTN, "SB": _BB_3BET_VS_SB,
}

# ---------------------------------------------------------------------------
# BB flat call vs each opener (NO premiums -- those go in the 3-bet range)
# Suited connectors, suited broadways, medium/small pairs, some offsuit
# ---------------------------------------------------------------------------

_BB_CALL_VS_LJ = {
    "TT": 1.0, "99": 1.0, "88": 1.0, "77": 1.0, "66": 1.0, "55": 1.0, "44": 1.0,
    "AJs": 1.0, "ATs": 1.0, "A9s": 1.0, "A8s": 1.0, "A7s": 1.0, "A6s": 1.0,
    "A5s": 1.0, "A4s": 1.0, "A3s": 1.0, "A2s": 1.0,
    "KQs": 1.0, "KJs": 1.0, "KTs": 1.0, "K9s": 1.0, "K8s": 1.0,
    "QJs": 1.0, "QTs": 1.0, "Q9s": 1.0,
    "JTs": 1.0, "J9s": 1.0,
    "T9s": 1.0, "T8s": 1.0,
    "98s": 1.0, "97s": 1.0,
    "87s": 1.0, "76s": 1.0, "65s": 1.0, "54s": 1.0,
    "AJo": 1.0, "ATo": 1.0, "A9o": 1.0,
    "KQo": 1.0, "KJo": 1.0,
    "QJo": 1.0,
}

_BB_CALL_VS_HJ = {
    **_BB_CALL_VS_LJ,
    "TT": 1.0, "55": 1.0, "44": 1.0, "33": 1.0,
    "AJs": 1.0, "A6s": 1.0, "A2s": 1.0,
    "KQs": 1.0, "K8s": 1.0,
    "Q9s": 1.0, "Q8s": 1.0,
    "J9s": 1.0, "J8s": 1.0,
    "T8s": 1.0,
    "98s": 1.0, "97s": 1.0,
    "87s": 1.0, "86s": 1.0, "76s": 1.0, "65s": 1.0, "54s": 1.0,
    "AJo": 1.0, "ATo": 1.0, "A9o": 1.0,
    "KQo": 1.0, "KJo": 1.0, "KTo": 1.0,
    "QJo": 1.0,
}

_BB_CALL_VS_CO = {
    **_BB_CALL_VS_HJ,
    "TT": 1.0, "55": 1.0, "44": 1.0, "33": 1.0, "22": 1.0,
    "A8s": 1.0, "A7s": 1.0, "A6s": 1.0, "A2s": 1.0,
    "K8s": 1.0, "K7s": 1.0,
    "Q8s": 1.0,
    "J8s": 1.0,
    "T8s": 1.0, "97s": 1.0,
    "86s": 1.0, "75s": 1.0, "65s": 1.0, "54s": 1.0,
    "A9o": 1.0,
    "KTo": 1.0,
    "QJo": 1.0, "QTo": 1.0,
    "JTo": 1.0,
}

_BB_CALL_VS_BTN = {
    **_BB_CALL_VS_CO,
    "55": 1.0, "44": 1.0, "33": 1.0, "22": 1.0,
    "A7s": 1.0, "A6s": 1.0, "A5s": 1.0, "A2s": 1.0,
    "K7s": 1.0, "K6s": 1.0,
    "Q8s": 1.0, "Q7s": 1.0,
    "J8s": 1.0,
    "T8s": 1.0, "97s": 1.0, "96s": 1.0,
    "86s": 1.0, "75s": 1.0,
    "A9o": 1.0, "A8o": 1.0,
    "KTo": 1.0, "K9o": 1.0,
    "QTo": 1.0, "Q9o": 1.0,
    "JTo": 1.0, "J9o": 1.0,
    "T9o": 1.0,
}

_BB_CALL_VS_SB = {
    **_BB_CALL_VS_BTN,
    "22": 1.0,
    "K6s": 1.0, "K5s": 1.0,
    "Q7s": 1.0,
    "96s": 1.0,
    "85s": 1.0, "75s": 1.0, "64s": 1.0,
    "A8o": 1.0, "A7o": 1.0,
    "K9o": 1.0,
    "Q9o": 1.0,
    "J9o": 1.0,
    "T9o": 1.0,
}

BB_CALL_RANGES: dict[str, dict[str, float]] = {
    "LJ": _BB_CALL_VS_LJ, "HJ": _BB_CALL_VS_HJ, "CO": _BB_CALL_VS_CO,
    "BTN": _BB_CALL_VS_BTN, "SB": _BB_CALL_VS_SB,
}

# ---------------------------------------------------------------------------
# Non-BB 3-bet ranges (any position 3-betting vs an open)
# Used when e.g. BTN 3-bets vs CO open
# ---------------------------------------------------------------------------

_IP_3BET_VS_EP = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0,
    "AKs": 1.0, "AQs": 1.0, "A5s": 1.0, "A4s": 1.0,
    "AKo": 1.0, "AQo": 1.0,
}

_IP_3BET_VS_MP = {
    **_IP_3BET_VS_EP,
    "JJ": 1.0, "TT": 1.0,
    "AQs": 1.0, "AJs": 1.0, "A4s": 1.0,
    "KQs": 1.0,
    "AQo": 1.0,
}

_IP_3BET_VS_LP = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
    "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0,
    "A5s": 1.0, "A4s": 1.0, "A3s": 1.0,
    "KQs": 1.0, "KJs": 1.0,
    "AKo": 1.0, "AQo": 1.0, "AJo": 1.0,
    "KQo": 1.0,
}

IP_3BET_RANGES: dict[str, dict[str, float]] = {
    "LJ": _IP_3BET_VS_EP, "HJ": _IP_3BET_VS_MP, "CO": _IP_3BET_VS_MP,
    "BTN": _IP_3BET_VS_LP, "SB": _IP_3BET_VS_LP,
}

# ---------------------------------------------------------------------------
# 4-bet ranges per position (vs a 3-bet)
# ---------------------------------------------------------------------------

_FOUR_BET_EP = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0,
    "AKs": 1.0, "A5s": 1.0,
    "AKo": 1.0,
}

_FOUR_BET_MP = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0,
    "AKs": 1.0, "AQs": 1.0, "A5s": 1.0,
    "AKo": 1.0,
}

_FOUR_BET_LP = {
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0,
    "AKs": 1.0, "AQs": 1.0, "A5s": 1.0, "A4s": 1.0,
    "AKo": 1.0, "AQo": 1.0,
}

FOUR_BET_RANGES: dict[str, dict[str, float]] = {
    "LJ": _FOUR_BET_EP, "HJ": _FOUR_BET_MP, "CO": _FOUR_BET_MP,
    "BTN": _FOUR_BET_LP, "SB": _FOUR_BET_LP, "BB": _FOUR_BET_LP,
}

# ---------------------------------------------------------------------------
# Position classification helpers
# ---------------------------------------------------------------------------

_EP_POSITIONS = {"LJ", "HJ"}
_MP_POSITIONS = {"CO"}
_LP_POSITIONS = {"BTN", "SB"}


def _opener_category(position: str) -> str:
    """Classify opener position for 3-bet range selection."""
    if position in _EP_POSITIONS:
        return "EP"
    if position in _MP_POSITIONS:
        return "MP"
    return "LP"


def get_starting_range(
    position: str,
    pot_type: str,
    vs_position: str | None = None,
    observed_freqs: dict[str, float] | None = None,
) -> dict[tuple[Card, Card], float]:
    """Get a starting range for a position and pot type.

    pot_type values:
      SRP       - single raised pot (opener's range or caller's range)
      THREE_BET - 3-bet pot (3-bettor's range)
      FOUR_BET  - 4-bet pot

    For BB in SRP, returns the flat-call range (no premiums).
    For BB in THREE_BET, returns the 3-bet range.
    vs_position indicates who the player was facing (the opener).

    Returns a combo-keyed range dict mapping (Card, Card) -> frequency.
    """
    gto: dict[str, float] = {}

    if pot_type == "SRP":
        if position == "BB":
            # BB flatted an open -- use call range keyed by opener
            vs = vs_position or "BTN"
            gto = BB_CALL_RANGES.get(vs, BB_CALL_RANGES["BTN"])
        else:
            # Opener's RFI range
            gto = OPEN_RANGES.get(position, {})

    elif pot_type == "THREE_BET":
        if position == "BB":
            vs = vs_position or "BTN"
            gto = BB_3BET_RANGES.get(vs, BB_3BET_RANGES["BTN"])
        else:
            # Non-BB 3-betting an open
            vs = vs_position or "CO"
            gto = IP_3BET_RANGES.get(vs, IP_3BET_RANGES["CO"])

    elif pot_type == "FOUR_BET":
        gto = FOUR_BET_RANGES.get(position, FOUR_BET_RANGES.get("BTN", {}))

    gto = dict(gto)

    if observed_freqs is None:
        return _expand_range_to_combos(gto)

    blended: dict[str, float] = {}
    all_keys = set(gto) | set(observed_freqs)
    for key in all_keys:
        g = gto.get(key, 0.0)
        o = observed_freqs.get(key, 0.0)
        blended[key] = GTO_WEIGHT * g + OBSERVED_WEIGHT * o
    return _expand_range_to_combos(blended)


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


def _expand_range_to_combos(
    hand_key_range: dict[str, float],
) -> dict[tuple[Card, Card], float]:
    """Convert a hand-key range to a combo-keyed range.

    Each hand key (e.g. 'AKs') is expanded to its specific combos,
    all inheriting the same frequency.
    """
    combo_range: dict[tuple[Card, Card], float] = {}
    for hand_key, freq in hand_key_range.items():
        if freq <= 0:
            continue
        for combo in _hand_key_to_combos(hand_key):
            combo_range[combo] = freq
    return combo_range


def _cards_conflict(combo: tuple[Card, Card], board: list[Card]) -> bool:
    """Check if a combo shares any card with the board."""
    for card in combo:
        for bc in board:
            if card.rank == bc.rank and card.suit == bc.suit:
                return True
    return False


def build_strength_map(
    combos: list[tuple[Card, Card]],
    board: list[Card],
) -> dict[tuple[Card, Card], float]:
    """Precompute average hand strength for each combo given a board.

    Uses eval7.evaluate() which returns higher scores for stronger hands.

    - River (5 board cards): evaluate 7-card hand directly
    - Turn (4 board cards): average over all remaining river cards
    - Flop (3 board cards): average over all remaining turn+river runouts
    """
    e7_board = [_card_to_eval7(c) for c in board]
    board_set = set(id(c) for c in e7_board)

    # Map each eval7 card to its (rank_val, suit_val) for conflict checking
    e7_to_key = {id(ec): (r, s) for (r, s), ec in _ALL_EVAL7_CARDS.items()}
    board_keys = {e7_to_key[id(c)] for c in e7_board}

    strength_map: dict[tuple[Card, Card], float] = {}
    n_board = len(board)

    for combo in combos:
        if _cards_conflict(combo, board):
            continue

        norm = _normalize_combo(combo)
        if norm in strength_map:
            continue

        e7_hand = [_card_to_eval7(c) for c in combo]
        hand_keys = {(c.rank.value, c.suit.value) for c in combo}
        excluded = board_keys | hand_keys

        if n_board == 5:
            # River: single evaluation
            strength_map[norm] = float(eval7.evaluate(e7_hand + e7_board))
        else:
            # Turn/Flop: average over possible runouts
            remaining = [c for c in _EVAL7_DECK
                         if e7_to_key[id(c)] not in excluded]
            cards_needed = 5 - n_board
            total = 0.0
            count = 0
            for runout in itertools.combinations(remaining, cards_needed):
                total += eval7.evaluate(e7_hand + e7_board + list(runout))
                count += 1
            strength_map[norm] = total / count if count > 0 else 0.0

    return strength_map



DAMPENING_FACTOR = 0.3


def filter_range_by_equity(
    range_: dict[tuple[Card, Card], float],
    board: list[Card],
    street: str,
    raise_pct: float,
    call_pct: float,
    strength_map: dict[tuple[Card, Card], float] | None = None,
    hard_split: bool = False,
) -> tuple[dict[tuple[Card, Card], float], dict[tuple[Card, Card], float], dict[tuple[Card, Card], float]]:
    """Split a range into raise/call/fold sub-ranges by equity ranking.

    Sorts combos by equity vs the full range, then assigns:
      - Top raise_pct to raising range
      - Next call_pct to calling range
      - Remainder to folding range

    When hard_split=False (default), uses soft filtering: combos in the
    matching bucket keep full weight, combos outside retain
    DAMPENING_FACTOR of their weight.  This prevents ranges from
    collapsing over multiple streets of narrowing.

    When hard_split=True, combos only appear in their assigned bucket.
    Use this for equity sub-range calculations where eval7 ignores
    weights and you need meaningful equity-vs-callers values.

    Returns (raising_range, calling_range, folding_range).
    """
    from solver.eq_calculator import all_hands_vs_range

    # Compute equity for each combo in range via eq_calculator
    valid_combos = [c for c, f in range_.items()
                    if f > 0 and not _cards_conflict(c, board)]

    if board and valid_combos:
        eq_map = all_hands_vs_range(valid_combos, range_, board)
    else:
        eq_map = {}

    equities: list[tuple[tuple[Card, Card], float, float]] = []
    for combo, freq in range_.items():
        if freq <= 0 or _cards_conflict(combo, board):
            continue
        eq = eq_map.get(_normalize_combo(combo), 0.5)
        equities.append((combo, freq, eq))

    # Sort by equity descending (strongest combos first)
    equities.sort(key=lambda x: x[2], reverse=True)

    total_combos = sum(freq for _, freq, _ in equities)
    if total_combos <= 0:
        return {}, {}, {}

    # First pass: determine which bucket each combo falls into
    buckets: list[str] = []  # "raise", "call", or "fold" per combo
    cumulative = 0.0
    raise_threshold = raise_pct / 100.0
    call_threshold = (raise_pct + call_pct) / 100.0

    for _, freq, _ in equities:
        position = cumulative / total_combos
        if position < raise_threshold:
            buckets.append("raise")
        elif position < call_threshold:
            buckets.append("call")
        else:
            buckets.append("fold")
        cumulative += freq

    # Second pass: assign weights based on split mode
    raising_range: dict[tuple[Card, Card], float] = {}
    calling_range: dict[tuple[Card, Card], float] = {}
    folding_range: dict[tuple[Card, Card], float] = {}

    for i, (combo, freq, _) in enumerate(equities):
        bucket = buckets[i]
        if hard_split:
            # Hard split: combos only in their bucket (for equity calc)
            if bucket == "raise":
                raising_range[combo] = freq
            elif bucket == "call":
                calling_range[combo] = freq
            else:
                folding_range[combo] = freq
        else:
            # Soft split: dampened presence in other buckets (for narrowing)
            if bucket == "raise":
                raising_range[combo] = freq
                calling_range[combo] = freq * DAMPENING_FACTOR
                folding_range[combo] = freq * DAMPENING_FACTOR
            elif bucket == "call":
                raising_range[combo] = freq * DAMPENING_FACTOR
                calling_range[combo] = freq
                folding_range[combo] = freq * DAMPENING_FACTOR
            else:
                raising_range[combo] = freq * DAMPENING_FACTOR
                calling_range[combo] = freq * DAMPENING_FACTOR
                folding_range[combo] = freq

    return raising_range, calling_range, folding_range
