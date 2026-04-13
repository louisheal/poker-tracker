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
import queue
import threading
from collections.abc import Iterator
from dataclasses import dataclass

import torch

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
    effective_stack_bb: float = 100.0  # min of both players' starting stacks in BB


def _card_token(card: Card) -> Token:
    return Token(
        token_type=TokenType.CARD,
        rank=RANK_TO_INDEX[card.rank],
        suit=SUIT_TO_INDEX[card.suit],
    )


def _action_token(action: Action, bet_size_pct: float, bet_size_bb: float = 0.0) -> Token:
    return Token(
        token_type=TokenType.ACTION,
        action=ACTION_TO_INDEX[action],
        bet_size_pct=bet_size_pct,
        bet_size_bb=bet_size_bb,
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


def _compute_bet_size_bb(action: PlayerAction, bb: float) -> float:
    """Compute action size in big blinds."""
    if bb <= 0:
        return 0.0
    if action.type == Action.BET and action.amount is not None:
        return action.amount / bb
    if action.type == Action.RAISE and action.raise_to is not None:
        return action.raise_to / bb
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

    For raises, raise_to is the total bet (including the call portion).
    We track round_invested per player to compute only the incremental
    amount added to the pot, matching how analyzers.py handles this.
    """
    bb = _big_blind_amount(ast)
    pot = sum(b.amount for b in ast.blinds) / bb

    pots: list[float] = []

    # Track each player's investment in the current betting round
    round_invested: dict[str, float] = {}
    for blind in ast.blinds:
        round_invested[blind.player] = round_invested.get(blind.player, 0.0) + blind.amount

    # Preflop actions
    for action in ast.preflop:
        pots.append(pot)
        player = action.player
        if action.type == Action.CALL and action.amount is not None:
            pot += action.amount / bb
            round_invested[player] = round_invested.get(player, 0.0) + action.amount
        elif action.type == Action.BET and action.amount is not None:
            pot += action.amount / bb
            round_invested[player] = round_invested.get(player, 0.0) + action.amount
        elif action.type == Action.RAISE and action.raise_to is not None:
            prev = round_invested.get(player, 0.0)
            new_money = action.raise_to - prev
            pot += new_money / bb
            round_invested[player] = action.raise_to

    # Postflop streets
    for street in [ast.flop, ast.turn, ast.river]:
        if street is None:
            break
        round_invested = {}
        for action in street.actions:
            pots.append(pot)
            player = action.player
            if action.type in (Action.BET, Action.CALL) and action.amount is not None:
                pot += action.amount / bb
                round_invested[player] = round_invested.get(player, 0.0) + action.amount
            elif action.type == Action.RAISE and action.raise_to is not None:
                prev = round_invested.get(player, 0.0)
                new_money = action.raise_to - prev
                pot += new_money / bb
                round_invested[player] = action.raise_to

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

    # Effective stack: min of both players' starting chips, in BB
    if len(ast.players) >= 2:
        chips = [chips for _, _, chips in ast.players]
        eff_stack_bb = min(chips) / bb if bb > 0 else 100.0
    else:
        eff_stack_bb = 100.0

    # Preflop actions -- encode pot type (SRP/3bet/4bet) and position context
    for action in ast.preflop:
        pot_before = pots[pot_idx] if pot_idx < len(pots) else 1.0
        size_pct = _compute_bet_size_pct(action, pot_before * bb)
        size_bb = _compute_bet_size_bb(action, bb)
        sequence.append(_action_token(action.type, size_pct, size_bb))
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
                        effective_stack_bb=eff_stack_bb,
                    ))
            else:
                # Both players are targets -- predict every action
                examples.append(TrainingExample(
                    sequence=list(sequence),
                    label=ACTION_TO_INDEX[action.type],
                    hand_id=ast.hand_id,
                    effective_stack_bb=eff_stack_bb,
                ))

            pot_before = pots[pot_idx] if pot_idx < len(pots) else 1.0
            size_pct = _compute_bet_size_pct(action, pot_before * bb)
            size_bb = _compute_bet_size_bb(action, bb)
            sequence.append(_action_token(action.type, size_pct, size_bb))
            pot_idx += 1

    return examples


def hand_id_hash(hand_id: str) -> int:
    """Deterministic hash of a hand ID for train/val splitting."""
    return int(hashlib.md5(hand_id.encode()).hexdigest(), 16)


from solver.augmentation import (
    SUIT_PERMUTATIONS,
    FLOP_ORDERINGS,
)

TENSOR_FIELDS = ("token_types", "ranks", "suits", "actions", "bet_sizes", "bet_sizes_bb", "street_ids", "padding_mask")
SCALAR_FIELDS = ("stack_sizes",)  # per-example scalars (not per-token)


def tensorize_all(examples: list[TrainingExample]) -> dict[str, torch.Tensor]:
    """Pre-tensorize all examples into stacked tensors.

    Returns a dict of tensors, each with shape (N, MAX_SEQ_LEN) plus
    a labels tensor of shape (N,). This is stored as a single .pt file
    and shared across DataLoader workers without duplication.

    Uses flat Python lists then bulk torch.tensor() conversion to avoid
    slow per-element tensor writes.
    """
    n = len(examples)
    PAD = MAX_SEQ_LEN

    all_token_types: list[list[int]] = []
    all_ranks: list[list[int]] = []
    all_suits: list[list[int]] = []
    all_actions: list[list[int]] = []
    all_bet_sizes: list[list[float]] = []
    all_bet_sizes_bb: list[list[float]] = []
    all_street_ids: list[list[int]] = []
    all_padding: list[list[bool]] = []
    all_labels: list[int] = []
    all_stack_sizes: list[float] = []

    street_marker_type = int(TokenType.STREET_MARKER)

    for ex in examples:
        seq = ex.sequence[:PAD]
        length = len(seq)
        pad_len = PAD - length

        all_token_types.append([int(t.token_type) for t in seq] + [0] * pad_len)
        all_ranks.append([t.rank for t in seq] + [0] * pad_len)
        all_suits.append([t.suit for t in seq] + [0] * pad_len)
        all_actions.append([t.action for t in seq] + [0] * pad_len)
        all_bet_sizes.append([t.bet_size_pct for t in seq] + [0.0] * pad_len)
        all_bet_sizes_bb.append([t.bet_size_bb for t in seq] + [0.0] * pad_len)
        all_street_ids.append(
            [t.action if int(t.token_type) == street_marker_type else 0 for t in seq]
            + [0] * pad_len
        )
        all_padding.append([False] * length + [True] * pad_len)
        all_labels.append(ex.label)
        all_stack_sizes.append(ex.effective_stack_bb / 100.0)  # normalize to ~0-3

    return {
        "token_types": torch.tensor(all_token_types, dtype=torch.int8),
        "ranks": torch.tensor(all_ranks, dtype=torch.int8),
        "suits": torch.tensor(all_suits, dtype=torch.int8),
        "actions": torch.tensor(all_actions, dtype=torch.int8),
        "bet_sizes": torch.tensor(all_bet_sizes, dtype=torch.float16),
        "bet_sizes_bb": torch.tensor(all_bet_sizes_bb, dtype=torch.float16),
        "street_ids": torch.tensor(all_street_ids, dtype=torch.int8),
        "padding_mask": torch.tensor(all_padding, dtype=torch.bool),
        "labels": torch.tensor(all_labels, dtype=torch.int8),
        "stack_sizes": torch.tensor(all_stack_sizes, dtype=torch.float16),
    }


# Lookup tables for GPU augmentation (moved to device lazily)
_SUIT_PERM_TENSOR = torch.tensor(SUIT_PERMUTATIONS, dtype=torch.long)   # (24, 4)
_FLOP_ORDER_TENSOR = torch.tensor(FLOP_ORDERINGS, dtype=torch.long)     # (6, 3)
_device_cache: dict[torch.device, dict[str, torch.Tensor]] = {}


def _get_lookup_tables(device: torch.device) -> dict[str, torch.Tensor]:
    """Cache lookup tables on the target device to avoid repeated transfers."""
    if device not in _device_cache:
        _device_cache[device] = {
            "suit_perms": _SUIT_PERM_TENSOR.to(device),
            "flop_orders": _FLOP_ORDER_TENSOR.to(device),
        }
    return _device_cache[device]


def augment_batch_gpu(batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Apply random suit permutation + flop reorder to a full batch on GPU.

    Operates entirely with vectorized tensor ops -- no Python loops over
    batch elements. Call after moving the batch to device, before the model.
    144x effective augmentation (24 suit perms x 6 flop orderings).
    """
    device = batch["token_types"].device
    B, S = batch["token_types"].shape
    tables = _get_lookup_tables(device)
    token_types = batch["token_types"]

    suits = batch["suits"].clone()
    ranks = batch["ranks"].clone()

    # --- Suit permutation (24 variants) ---
    perm_indices = torch.randint(0, 24, (B,), device=device)
    perm_map = tables["suit_perms"][perm_indices]               # (B, 4)
    card_mask = token_types == int(TokenType.CARD)              # (B, S)
    new_suits = torch.gather(perm_map, 1, suits.clamp(0, 3))   # (B, S)
    suits = torch.where(card_mask, new_suits, suits)

    # --- Flop reorder (6 variants) ---
    order_indices = torch.randint(0, 6, (B,), device=device)
    orderings = tables["flop_orders"][order_indices]             # (B, 3)

    # Find the flop marker (STREET_MARKER with action=0) per example
    is_flop_marker = (
        (token_types == int(TokenType.STREET_MARKER))
        & (batch["actions"] == 0)
    )
    has_flop = is_flop_marker.any(dim=1)                        # (B,)
    flop_pos = is_flop_marker.int().argmax(dim=1)               # (B,)

    # Positions of the 3 flop cards: flop_pos + [1, 2, 3]
    offsets = torch.arange(1, 4, device=device)
    flop_card_pos = flop_pos.unsqueeze(1) + offsets.unsqueeze(0)  # (B, 3)
    flop_card_pos = flop_card_pos.clamp(max=S - 1)

    # Gather original flop card values, reorder, scatter back
    orig_ranks = torch.gather(ranks, 1, flop_card_pos)
    orig_suits = torch.gather(suits, 1, flop_card_pos)
    reordered_ranks = torch.gather(orig_ranks, 1, orderings)
    reordered_suits = torch.gather(orig_suits, 1, orderings)

    flop_mask = has_flop.unsqueeze(1).expand_as(flop_card_pos)
    ranks.scatter_(1, flop_card_pos, torch.where(flop_mask, reordered_ranks, orig_ranks))
    suits.scatter_(1, flop_card_pos, torch.where(flop_mask, reordered_suits, orig_suits))

    return {**batch, "suits": suits, "ranks": ranks}


def compact_data(data: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Downcast tensors to compact dtypes to reduce memory.

    int64 -> int8 for small-range integer fields, float32 -> float16 for bet sizes.
    Data stays on CPU. batch_iterator handles device transfer and upcasting.
    """
    compact_int = {"token_types", "ranks", "suits", "actions", "street_ids", "labels"}
    result: dict[str, torch.Tensor] = {}
    for k, v in data.items():
        if k in compact_int and v.dtype != torch.int8:
            result[k] = v.to(torch.int8)
        elif k in ("bet_sizes", "bet_sizes_bb") and v.dtype != torch.float16:
            result[k] = v.to(torch.float16)
        else:
            result[k] = v
    return result


# Dtype casts needed per batch for model compatibility (embeddings need long)
_LONG_FIELDS = ("token_types", "ranks", "suits", "actions", "street_ids")


def batch_iterator(
    data: dict[str, torch.Tensor],
    batch_size: int,
    shuffle: bool = True,
    device: torch.device | None = None,
) -> Iterator[dict[str, torch.Tensor]]:
    """Yield batches by slicing pre-tensorized CPU data, transferring to device.

    Data lives on CPU in compact int8/float16 dtypes.
    Each batch is sliced, cast to model-compatible dtypes, and moved to device.
    """
    n = data["labels"].shape[0]
    indices = torch.randperm(n) if shuffle else torch.arange(n)

    for start in range(0, n, batch_size):
        idx = indices[start:start + batch_size]
        batch: dict[str, torch.Tensor] = {}
        for key in TENSOR_FIELDS:
            val = data[key][idx]
            batch[key] = val.long() if key in _LONG_FIELDS else val
        for key in SCALAR_FIELDS:
            if key in data:
                batch[key] = data[key][idx].float()
        batch["labels"] = data["labels"][idx].long()
        batch["bet_sizes"] = batch["bet_sizes"].float()
        batch["bet_sizes_bb"] = batch["bet_sizes_bb"].float()
        if device is not None:
            batch = {k: v.to(device, non_blocking=True) for k, v in batch.items()}
        yield batch


def _prepare_batch(
    data: dict[str, torch.Tensor],
    idx: torch.Tensor,
    device: torch.device | None,
) -> dict[str, torch.Tensor]:
    """Slice one batch from CPU data, cast dtypes, move to device."""
    batch: dict[str, torch.Tensor] = {}
    for key in TENSOR_FIELDS:
        val = data[key][idx]
        batch[key] = val.long() if key in _LONG_FIELDS else val
    for key in SCALAR_FIELDS:
        if key in data:
            batch[key] = data[key][idx].float()
    batch["labels"] = data["labels"][idx].long()
    batch["bet_sizes"] = batch["bet_sizes"].float()
    batch["bet_sizes_bb"] = batch["bet_sizes_bb"].float()
    if device is not None:
        batch = {k: v.to(device, non_blocking=True) for k, v in batch.items()}
    return batch


def prefetch_batch_iterator(
    data: dict[str, torch.Tensor],
    batch_size: int,
    shuffle: bool = True,
    device: torch.device | None = None,
    num_workers: int = 2,
    prefetch_depth: int = 4,
) -> Iterator[dict[str, torch.Tensor]]:
    """Like batch_iterator but with threaded prefetching.

    Worker threads prepare batches on CPU in parallel, filling a queue
    so the GPU always has work ready. Workers share memory (no copying)
    and PyTorch tensor ops release the GIL.
    """
    n = data["labels"].shape[0]
    indices = torch.randperm(n) if shuffle else torch.arange(n)

    all_idx = [indices[start:start + batch_size] for start in range(0, n, batch_size)]
    num_batches = len(all_idx)

    work_q: queue.Queue[torch.Tensor | None] = queue.Queue()
    done_q: queue.Queue[dict[str, torch.Tensor] | BaseException] = queue.Queue(maxsize=prefetch_depth)

    for idx in all_idx:
        work_q.put(idx)
    for _ in range(num_workers):
        work_q.put(None)

    def _worker() -> None:
        while True:
            idx = work_q.get()
            if idx is None:
                return
            try:
                done_q.put(_prepare_batch(data, idx, device))
            except Exception as exc:
                done_q.put(exc)
                return

    threads = [threading.Thread(target=_worker, daemon=True) for _ in range(num_workers)]
    for t in threads:
        t.start()

    for _ in range(num_batches):
        item = done_q.get()
        if isinstance(item, BaseException):
            raise item
        yield item

    for t in threads:
        t.join()
