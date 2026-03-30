"""Training data extraction from parsed hand histories.

Walks HandAST objects and produces training examples. Multiple examples per
hand -- one per decision point where we predict the next action.

Key design:
  - Uses ALL hands where 2 players see the flop (not just showdown hands)
  - No hole cards in model input (board + actions only)
  - Hero hands: predict villain's actions (hero actions are context)
  - Non-hero hands (hhd_ files): predict every action (both players are targets)
  - Preflop actions are included so the model learns pot type / position context
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset

from app.models.enums import Action
from app.parsers.ast import HandAST, PlayerAction, Street
from playing_cards_lib.core import Card, Rank, Suit
from solver.models import Token, TokenType

RANK_TO_INDEX = {r: i for i, r in enumerate(Rank)}
SUIT_TO_INDEX = {s: i for i, s in enumerate(Suit)}

ACTION_TO_INDEX = {
    Action.FOLD: 0,
    Action.CHECK: 1,
    Action.CALL: 2,
    Action.BET: 3,
    Action.RAISE: 4,
}

MAX_SEQ_LEN = 64


@dataclass
class TrainingExample:
    """One training example: a token sequence up to a decision point,
    plus the actual next action as the label."""
    sequence: list[Token]
    label: int  # next action index (0-4)
    hand_id: str = ""  # for train/val splitting by hand


def _card_token(card: Card) -> Token:
    return Token(
        token_type=TokenType.CARD,
        rank=RANK_TO_INDEX[card.rank],
        suit=SUIT_TO_INDEX[card.suit],
    )


def _action_token(action: Action, bet_size_pct: float) -> Token:
    return Token(
        token_type=TokenType.ACTION,
        action=ACTION_TO_INDEX[action],
        bet_size_pct=bet_size_pct,
    )


def _street_marker(street_idx: int) -> Token:
    """street_idx: 0=FLOP, 1=TURN, 2=RIVER."""
    return Token(token_type=TokenType.STREET_MARKER, action=street_idx)


def _big_blind_amount(ast: HandAST) -> float:
    """Extract the big blind amount from the blinds."""
    for blind in ast.blinds:
        if not blind.is_small and blind.amount > 0:
            return blind.amount
    amounts = [b.amount for b in ast.blinds if b.amount > 0]
    return max(amounts) if amounts else 1.0


def _compute_bet_size_pct(action: PlayerAction, pot: float) -> float:
    """Compute action size as a percentage of the pot."""
    if pot <= 0:
        return 0.0
    if action.type == Action.BET and action.amount is not None:
        return (action.amount / pot) * 100.0
    if action.type == Action.RAISE and action.raise_to is not None:
        return (action.raise_to / pot) * 100.0
    return 0.0


def is_heads_up_postflop(ast: HandAST) -> bool:
    """Check if exactly 2 players saw the flop."""
    if ast.flop is None:
        return False
    active_players = {player for player, _, _ in ast.players}
    for action in ast.preflop:
        if action.type == Action.FOLD:
            active_players.discard(action.player)
    return len(active_players) == 2


def compute_running_pot(ast: HandAST) -> tuple[list[float], float]:
    """Compute pot size in BB before each action (preflop + postflop).

    Returns (list of pot-before-each-action, bb_amount).
    """
    bb = _big_blind_amount(ast)
    pot = sum(b.amount for b in ast.blinds) / bb

    pots: list[float] = []

    # Preflop actions
    for action in ast.preflop:
        pots.append(pot)
        if action.type == Action.CALL and action.amount is not None:
            pot += action.amount / bb
        elif action.type == Action.BET and action.amount is not None:
            pot += action.amount / bb
        elif action.type == Action.RAISE and action.raise_to is not None:
            pot += action.raise_to / bb

    # Postflop streets
    for street in [ast.flop, ast.turn, ast.river]:
        if street is None:
            break
        for action in street.actions:
            pots.append(pot)
            if action.type in (Action.BET, Action.CALL) and action.amount is not None:
                pot += action.amount / bb
            elif action.type == Action.RAISE and action.raise_to is not None:
                pot += action.raise_to / bb

    return pots, bb


def extract_training_examples(ast: HandAST) -> list[TrainingExample]:
    """Extract training examples from any heads-up postflop hand.

    Hero hands: one example per villain decision point.
    Non-hero hands: one example per action (both players are targets).
    No hole cards in the sequence -- model sees only actions + board.
    Preflop actions are included so the model can infer pot type and position.
    """
    if not is_heads_up_postflop(ast):
        return []

    is_hero_hand = ast.hero_hole_cards is not None
    pots, bb = compute_running_pot(ast)
    pot_idx = 0
    sequence: list[Token] = []
    examples: list[TrainingExample] = []

    # Preflop actions -- encode pot type (SRP/3bet/4bet) and position context
    for action in ast.preflop:
        pot_before = pots[pot_idx] if pot_idx < len(pots) else 1.0
        size_pct = _compute_bet_size_pct(action, pot_before * bb)
        sequence.append(_action_token(action.type, size_pct))
        pot_idx += 1

    # Postflop streets
    streets: list[tuple[int, Street | None]] = [
        (0, ast.flop),
        (1, ast.turn),
        (2, ast.river),
    ]

    for street_idx, street in streets:
        if street is None:
            break

        sequence.append(_street_marker(street_idx))
        for card in street.cards:
            sequence.append(_card_token(card))

        for action in street.actions:
            if is_hero_hand:
                # Only predict villain's actions (hero actions are context)
                if not action.is_hero:
                    examples.append(TrainingExample(
                        sequence=list(sequence),
                        label=ACTION_TO_INDEX[action.type],
                        hand_id=ast.hand_id,
                    ))
            else:
                # Both players are targets -- predict every action
                examples.append(TrainingExample(
                    sequence=list(sequence),
                    label=ACTION_TO_INDEX[action.type],
                    hand_id=ast.hand_id,
                ))

            pot_before = pots[pot_idx] if pot_idx < len(pots) else 1.0
            size_pct = _compute_bet_size_pct(action, pot_before * bb)
            sequence.append(_action_token(action.type, size_pct))
            pot_idx += 1

    return examples


def hand_id_hash(hand_id: str) -> int:
    """Deterministic hash of a hand ID for train/val splitting."""
    return int(hashlib.md5(hand_id.encode()).hexdigest(), 16)


def tensorize_example(tokens: list[Token], label: int) -> dict[str, torch.Tensor]:
    """Convert a token list + label to padded tensors."""
    seq = tokens[:MAX_SEQ_LEN]
    length = len(seq)

    token_types = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    ranks = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    suits = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    actions = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    bet_sizes = torch.zeros(MAX_SEQ_LEN, dtype=torch.float)
    street_ids = torch.zeros(MAX_SEQ_LEN, dtype=torch.long)
    padding_mask = torch.ones(MAX_SEQ_LEN, dtype=torch.bool)

    for i, tok in enumerate(seq):
        token_types[i] = int(tok.token_type)
        ranks[i] = tok.rank
        suits[i] = tok.suit
        actions[i] = tok.action
        bet_sizes[i] = tok.bet_size_pct
        street_ids[i] = tok.action if tok.token_type == TokenType.STREET_MARKER else 0
        padding_mask[i] = False

    return {
        "token_types": token_types,
        "ranks": ranks,
        "suits": suits,
        "actions": actions,
        "bet_sizes": bet_sizes,
        "street_ids": street_ids,
        "padding_mask": padding_mask,
        "label": torch.tensor(label, dtype=torch.long),
    }


import itertools
import random

from solver.augmentation import (
    SUIT_PERMUTATIONS,
    FLOP_ORDERINGS,
    apply_suit_permutation,
    apply_flop_reorder,
)


class PokerDataset(Dataset):
    """PyTorch dataset wrapping a list of TrainingExamples.

    When augment=True, applies random suit permutation + flop reorder
    on-the-fly per __getitem__ call (144x effective augmentation).
    """

    def __init__(self, examples: list[TrainingExample], augment: bool = False) -> None:
        self.examples = examples
        self.augment = augment

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        ex = self.examples[idx]
        tokens = list(ex.sequence)

        if self.augment:
            perm = random.choice(SUIT_PERMUTATIONS)
            tokens = apply_suit_permutation(tokens, perm)
            ordering = random.choice(FLOP_ORDERINGS)
            tokens = apply_flop_reorder(tokens, ordering)

        return tensorize_example(tokens, ex.label)


def collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    """Collate a batch of tensorized examples, trimming padding to batch max length."""
    max_len = max((~b["padding_mask"]).sum().item() for b in batch)
    max_len = int(max_len)

    result: dict[str, list[torch.Tensor]] = {
        "token_types": [],
        "ranks": [],
        "suits": [],
        "actions": [],
        "bet_sizes": [],
        "street_ids": [],
        "padding_mask": [],
        "labels": [],
    }

    for b in batch:
        for key in ("token_types", "ranks", "suits", "actions", "bet_sizes", "street_ids", "padding_mask"):
            result[key].append(b[key][:max_len])
        result["labels"].append(b["label"])

    return {
        "token_types": torch.stack(result["token_types"]),
        "ranks": torch.stack(result["ranks"]),
        "suits": torch.stack(result["suits"]),
        "actions": torch.stack(result["actions"]),
        "bet_sizes": torch.stack(result["bet_sizes"]),
        "street_ids": torch.stack(result["street_ids"]),
        "padding_mask": torch.stack(result["padding_mask"]),
        "labels": torch.stack(result["labels"]),
    }
