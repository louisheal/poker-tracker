"""Equity calculator wrapping eval7's C-level equity functions.

Provides a clean interface using our playing_cards_lib types while
delegating the heavy computation to eval7:
  - River (5 cards): exact enumeration via py_all_hands_vs_range
  - Flop/Turn (<5 cards): Monte Carlo via py_all_hands_vs_range

Usage:
    from solver.eq_calculator import all_hands_vs_range

    equities = all_hands_vs_range(hero_combos, villain_range, board)
    # equities: dict mapping normalized combo -> float equity [0, 1]
"""

from __future__ import annotations

import eval7

from playing_cards_lib.core import Card, Rank, Suit

# Pre-built eval7 Card lookup keyed by (rank_value, suit_value)
_ALL_EVAL7_CARDS: dict[tuple[str, str], eval7.Card] = {
    (r.value, s.value): eval7.Card(f"{r.value}{s.value.lower()}")
    for r in Rank
    for s in Suit
}

# Canonical ordering for normalizing combo tuples
_RANK_ORDER = {r: i for i, r in enumerate(Rank)}
_SUIT_ORDER = {s: i for i, s in enumerate(Suit)}

DEFAULT_MC_ITERATIONS = 10_000


def _card_to_eval7(card: Card) -> eval7.Card:
    """Convert a playing_cards_lib Card to an eval7 Card."""
    return _ALL_EVAL7_CARDS[(card.rank.value, card.suit.value)]


def _normalize_combo(combo: tuple[Card, Card]) -> tuple[Card, Card]:
    """Normalize combo tuple ordering for consistent dict lookups."""
    a, b = combo
    ka = (_RANK_ORDER[a.rank], _SUIT_ORDER[a.suit])
    kb = (_RANK_ORDER[b.rank], _SUIT_ORDER[b.suit])
    if ka > kb:
        return (b, a)
    return combo


def _cards_conflict_with_board(
    combo: tuple[Card, Card], board: list[Card]
) -> bool:
    """Check if a combo shares any card with the board."""
    for card in combo:
        for bc in board:
            if card.rank == bc.rank and card.suit == bc.suit:
                return True
    return False


def _to_eval7_range(
    range_: dict[tuple[Card, Card], float],
    board: list[Card],
) -> list[tuple[tuple[eval7.Card, eval7.Card], float]]:
    """Convert our range dict to eval7-compatible iterable.

    Filters out combos with freq <= 0 or that conflict with the board.
    Weights are passed through (eval7 ignores them but we include for
    compatibility with its expected format).
    """
    result = []
    for combo, freq in range_.items():
        if freq <= 0 or _cards_conflict_with_board(combo, board):
            continue
        e7_combo = (_card_to_eval7(combo[0]), _card_to_eval7(combo[1]))
        result.append((e7_combo, freq))
    return result


def _to_eval7_hero(
    combos: list[tuple[Card, Card]],
    board: list[Card],
) -> list[tuple[tuple[eval7.Card, eval7.Card], float]]:
    """Convert hero combo list to eval7-compatible iterable.

    Filters out combos that conflict with the board.
    """
    result = []
    for combo in combos:
        if _cards_conflict_with_board(combo, board):
            continue
        e7_combo = (_card_to_eval7(combo[0]), _card_to_eval7(combo[1]))
        result.append((e7_combo, 1.0))
    return result


def _eval7_hand_to_combo(
    e7_hand: tuple[eval7.Card, ...],
) -> tuple[Card, Card]:
    """Convert an eval7 hand tuple back to a normalized playing_cards_lib combo."""
    rank_map = {
        "A": Rank.ACE, "K": Rank.KING, "Q": Rank.QUEEN, "J": Rank.JACK,
        "T": Rank.TEN, "9": Rank.NINE, "8": Rank.EIGHT, "7": Rank.SEVEN,
        "6": Rank.SIX, "5": Rank.FIVE, "4": Rank.FOUR, "3": Rank.THREE,
        "2": Rank.TWO,
    }
    suit_map = {
        "s": Suit.SPADES, "h": Suit.HEARTS,
        "d": Suit.DIAMONDS, "c": Suit.CLUBS,
    }
    card_strs = [str(c) for c in e7_hand]
    c0 = Card(rank_map[card_strs[0][0]], suit_map[card_strs[0][1]])
    c1 = Card(rank_map[card_strs[1][0]], suit_map[card_strs[1][1]])
    return _normalize_combo((c0, c1))


def all_hands_vs_range(
    hero_combos: list[tuple[Card, Card]],
    villain_range: dict[tuple[Card, Card], float],
    board: list[Card],
    iterations: int = DEFAULT_MC_ITERATIONS,
) -> dict[tuple[Card, Card], float]:
    """Compute equity of each hero combo vs a villain range on the given board.

    Args:
        hero_combos: List of hero hole card combos to evaluate.
        villain_range: Dict mapping villain combos to frequency weights.
            Combos with freq <= 0 are excluded. Note: eval7 treats all
            combos equally (ignores weights).
        board: Community cards (3 for flop, 4 for turn, 5 for river).
        iterations: Monte Carlo iterations for flop/turn. Ignored on river
            where exact evaluation is used automatically.

    Returns:
        Dict mapping each normalized hero combo to its equity [0.0, 1.0].
        Board-conflicting combos get 0.5 (default equity).
        Combos impossible due to card removal get excluded.
    """
    if not board or not hero_combos or not villain_range:
        return {_normalize_combo(c): 0.5 for c in hero_combos}

    e7_board = tuple(_card_to_eval7(c) for c in board)
    e7_hero = _to_eval7_hero(hero_combos, board)
    e7_villain = _to_eval7_range(villain_range, board)

    if not e7_hero or not e7_villain:
        return {_normalize_combo(c): 0.5 for c in hero_combos}

    # On river, pass iterations >= villain count to trigger exact mode
    if len(board) == 5:
        iters = max(len(e7_villain), iterations)
    else:
        iters = iterations

    e7_result = eval7.py_all_hands_vs_range(e7_hero, e7_villain, e7_board, iters)

    # Map eval7 results back to our combo format
    result: dict[tuple[Card, Card], float] = {}
    for e7_hand, equity in e7_result.items():
        if equity == -1:
            continue
        norm = _eval7_hand_to_combo(e7_hand)
        result[norm] = float(equity)

    # Fill in board-conflicting combos with default 0.5
    for combo in hero_combos:
        norm = _normalize_combo(combo)
        if norm not in result:
            result[norm] = 0.5

    return result
