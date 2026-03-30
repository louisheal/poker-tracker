"""Training data extraction from parsed hand histories.

Walks HandAST objects and produces training examples -- one per villain
decision point where villain's cards are known (showdown hands).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import IntEnum

import torch
from torch.utils.data import Dataset

from app.models.enums import Action
from app.parsers.ast import HandAST, PlayerAction, Street
from playing_cards_lib.core import Card, Rank, Suit

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


@dataclass
class TrainingExample:
    """One training example: a sequence of tokens up to a villain decision
    point, plus the villain's chosen action as the label."""
    sequence: list[Token]
    label: int  # villain's action index (0-4)


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
        if not blind.is_small:
            return blind.amount
    # Fallback: largest blind
    return max((b.amount for b in ast.blinds), default=1.0)


def _compute_bet_size_pct(action: PlayerAction, pot: float) -> float:
    """Compute action size as a percentage of the pot."""
    if pot <= 0:
        return 0.0
    if action.type == Action.BET and action.amount is not None:
        return (action.amount / pot) * 100.0
    if action.type == Action.RAISE and action.raise_to is not None:
        return (action.raise_to / pot) * 100.0
    return 0.0


def _get_villain_name(ast: HandAST) -> str | None:
    """Find the non-hero player who showed cards."""
    for name in ast.shown_cards:
        if name != "Hero":
            return name
    return None


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
    """Extract training examples from a hand where villain's cards are known.

    Each example captures the game state up to a villain decision point.
    The label is the action the villain actually took.
    """
    if ast.hero_hole_cards is None:
        return []

    villain_name = _get_villain_name(ast)
    if villain_name is None:
        return []

    villain_cards = ast.shown_cards.get(villain_name)
    if villain_cards is None:
        return []

    pots, bb = compute_running_pot(ast)
    pot_idx = 0
    sequence: list[Token] = []
    examples: list[TrainingExample] = []

    # Add hero hole cards
    sequence.append(_card_token(ast.hero_hole_cards.fst_card))
    sequence.append(_card_token(ast.hero_hole_cards.snd_card))

    # Add villain hole cards
    sequence.append(_card_token(villain_cards.fst_card))
    sequence.append(_card_token(villain_cards.snd_card))

    # Preflop actions
    for action in ast.preflop:
        if action.player == villain_name:
            examples.append(TrainingExample(
                sequence=list(sequence),
                label=ACTION_TO_INDEX[action.type],
            ))

        pot_before = pots[pot_idx] if pot_idx < len(pots) else 1.0
        size_pct = _compute_bet_size_pct(action, pot_before * bb) / bb if bb > 0 else 0.0
        # Normalize: use pot-relative sizing
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

        # Street marker
        sequence.append(_street_marker(street_idx))

        # Community cards
        for card in street.cards:
            sequence.append(_card_token(card))

        # Street actions
        for action in street.actions:
            if action.player == villain_name:
                examples.append(TrainingExample(
                    sequence=list(sequence),
                    label=ACTION_TO_INDEX[action.type],
                ))

            pot_before = pots[pot_idx] if pot_idx < len(pots) else 1.0
            size_pct = _compute_bet_size_pct(action, pot_before * bb)
            sequence.append(_action_token(action.type, size_pct))
            pot_idx += 1

    return examples


def hand_id_hash(hand_id: str) -> int:
    """Deterministic hash of a hand ID for train/val splitting."""
    return int(hashlib.md5(hand_id.encode()).hexdigest(), 16)


def tensorize_example(ex: TrainingExample) -> dict[str, torch.Tensor]:
    """Convert a TrainingExample to padded tensors."""
    seq = ex.sequence[:MAX_SEQ_LEN]
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
        "label": torch.tensor(ex.label, dtype=torch.long),
    }


class PokerDataset(Dataset):
    """PyTorch dataset wrapping a list of TrainingExamples.

    When augment=True, applies a random suit permutation on-the-fly
    per __getitem__ call. This avoids pre-generating all 576 variants
    and keeps memory usage proportional to the base example count.
    """

    def __init__(self, examples: list[TrainingExample], augment: bool = False) -> None:
        self.examples = examples
        self.augment = augment

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        ex = self.examples[idx]
        if self.augment:
            ex = _random_suit_permute(ex)
        return tensorize_example(ex)


def _random_suit_permute(ex: TrainingExample) -> TrainingExample:
    """Apply a random suit permutation to all card tokens in an example.

    This is the dominant augmentation (24 of the 576 variants).
    Flop reordering and hole card swaps have minimal impact on the
    token sequence since the model sees the same cards regardless of order.
    """
    import random
    perm = list(range(4))
    random.shuffle(perm)

    new_seq = []
    for tok in ex.sequence:
        if tok.token_type == TokenType.CARD:
            new_seq.append(Token(
                token_type=TokenType.CARD,
                rank=tok.rank,
                suit=perm[tok.suit],
            ))
        else:
            new_seq.append(tok)

    return TrainingExample(sequence=new_seq, label=ex.label)


def collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    """Collate a batch of tensorized examples, trimming padding to batch max length."""
    # Find the max non-padded length in this batch
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
