"""Data augmentation for poker hand histories.

Generates augmented variants of a hand by applying symmetry transformations
that preserve the game-theoretic properties:
  - Suit permutation (24 variants): all suits are strategically equivalent
  - Flop reordering (6 variants): flop card order is irrelevant
  - Hole card swaps (4 variants): order of hole cards is irrelevant

Total augmentation factor: 24 x 6 x 4 = 576 variants per hand.
"""

from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards
from app.parsers.ast import HandAST, PlayerAction, BlindPost, Street

SUITS = list(Suit)
SUIT_PERMUTATIONS = list(itertools.permutations(range(4)))  # 24 permutations
FLOP_ORDERINGS = list(itertools.permutations(range(3)))     # 6 orderings


def _remap_card(card: Card, perm: tuple[int, ...]) -> Card:
    """Apply a suit permutation to a single card."""
    old_idx = SUITS.index(card.suit)
    new_suit = SUITS[perm[old_idx]]
    return Card(card.rank, new_suit)


def _remap_hole_cards(hc: HoleCards, perm: tuple[int, ...]) -> HoleCards:
    """Apply a suit permutation to hole cards."""
    return HoleCards(
        _remap_card(hc.fst_card, perm),
        _remap_card(hc.snd_card, perm),
    )


def _remap_action(action: PlayerAction, perm: tuple[int, ...]) -> PlayerAction:
    """Actions don't contain cards, so just copy."""
    return PlayerAction(
        player=action.player,
        type=action.type,
        amount=action.amount,
        raise_to=action.raise_to,
        is_hero=action.is_hero,
    )


def _remap_street(street: Street | None, perm: tuple[int, ...]) -> Street | None:
    if street is None:
        return None
    return Street(
        cards=[_remap_card(c, perm) for c in street.cards],
        actions=[_remap_action(a, perm) for a in street.actions],
    )


def suit_rotate(ast: HandAST, perm: tuple[int, ...]) -> HandAST:
    """Apply a suit permutation to all cards in the hand."""
    new_ast = copy.copy(ast)

    if ast.hero_hole_cards is not None:
        new_ast.hero_hole_cards = _remap_hole_cards(ast.hero_hole_cards, perm)

    new_ast.blinds = list(ast.blinds)
    new_ast.preflop = [_remap_action(a, perm) for a in ast.preflop]
    new_ast.flop = _remap_street(ast.flop, perm)
    new_ast.turn = _remap_street(ast.turn, perm)
    new_ast.river = _remap_street(ast.river, perm)

    new_ast.shown_cards = {
        name: _remap_hole_cards(hc, perm)
        for name, hc in ast.shown_cards.items()
    }

    return new_ast


def flop_rotate(ast: HandAST, ordering: tuple[int, ...]) -> HandAST:
    """Reorder the 3 flop cards. Game state is identical regardless of order."""
    if ast.flop is None or len(ast.flop.cards) != 3:
        return ast

    new_ast = copy.copy(ast)
    new_ast.flop = Street(
        cards=[ast.flop.cards[i] for i in ordering],
        actions=list(ast.flop.actions),
    )
    return new_ast


def hole_card_swap(ast: HandAST, swap_hero: bool, swap_villain: bool) -> HandAST:
    """Swap the order of hole cards for hero and/or villain.

    HoleCards constructor auto-sorts by rank, so we need to bypass
    that by directly constructing with swapped cards.
    """
    new_ast = copy.copy(ast)

    if swap_hero and ast.hero_hole_cards is not None:
        # Create new HoleCards with swapped order
        new_ast.hero_hole_cards = HoleCards(
            ast.hero_hole_cards.snd_card,
            ast.hero_hole_cards.fst_card,
        )

    if swap_villain:
        new_shown: dict[str, HoleCards] = {}
        for name, hc in ast.shown_cards.items():
            if name != "Hero":
                new_shown[name] = HoleCards(hc.snd_card, hc.fst_card)
            else:
                new_shown[name] = hc
        new_ast.shown_cards = new_shown

    return new_ast


def augment_hand(ast: HandAST) -> list[HandAST]:
    """Generate all 576 augmented variants of a hand.

    Applies all combinations of:
      - 24 suit permutations
      - 6 flop orderings
      - 4 hole card swap combinations (hero x villain)
    """
    variants: list[HandAST] = []

    for suit_perm in SUIT_PERMUTATIONS:
        suit_rotated = suit_rotate(ast, suit_perm)
        for flop_order in FLOP_ORDERINGS:
            flop_rotated = flop_rotate(suit_rotated, flop_order)
            for swap_h in (False, True):
                for swap_v in (False, True):
                    variants.append(hole_card_swap(flop_rotated, swap_h, swap_v))

    return variants
