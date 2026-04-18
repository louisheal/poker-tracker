"""Data augmentation for poker training sequences.

Provides augmentation constants and GPU batch augmentation:
  - Suit permutation (24 variants): all suits are strategically equivalent
  - Flop reordering (6 variants): flop card order is irrelevant

Total effective augmentation: 24 x 6 = 144 variants per example.
Applied per-batch on GPU via augment_batch_gpu() in dataset.py.

Note: Hole card swap is removed -- no hole cards are in the model input.
"""

from __future__ import annotations

import itertools
from solver.models import Token, TokenType

SUIT_PERMUTATIONS = list(itertools.permutations(range(4)))  # 24 permutations
FLOP_ORDERINGS = list(itertools.permutations(range(3)))     # 6 orderings


def apply_suit_permutation(tokens: list[Token], perm: tuple[int, ...]) -> list[Token]:
    """Apply a suit permutation to all card tokens in a sequence."""
    result = []
    for t in tokens:
        if t.token_type == TokenType.CARD:
            result.append(Token(
                token_type=TokenType.CARD,
                rank=t.rank,
                suit=perm[t.suit],
            ))
        else:
            result.append(t)
    return result


def apply_flop_reorder(tokens: list[Token], ordering: tuple[int, ...]) -> list[Token]:
    """Reorder the 3 flop card tokens within a sequence.

    Finds the flop street marker (action=0, type=STREET_MARKER) and
    reorders the next 3 card tokens according to the given ordering.
    """
    result = list(tokens)
    for i, tok in enumerate(result):
        if tok.token_type == TokenType.STREET_MARKER and tok.action == 0:
            flop_start = i + 1
            if flop_start + 3 <= len(result):
                flop_cards = [result[flop_start + j] for j in range(3)]
                if all(c.token_type == TokenType.CARD for c in flop_cards):
                    for j, idx in enumerate(ordering):
                        result[flop_start + j] = flop_cards[idx]
            break
    return result
