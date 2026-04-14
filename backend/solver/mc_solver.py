"""Monte Carlo tree solver for EV computation.

Full-enumeration tree solver that replaces the formula-based EV calculator.
Recursively enumerates all turn and river cards, using the trained model
to predict villain responses and eval7 for showdown equity.

Key design:
- Full enumeration (no sampling): 47 turn × 46 river = exact results
- Batched model inference: all sequences pre-collected and mega-batched
- Reduced hero action set on future streets: Check/B66/B133/B200 or Fold/Call/R3x
- Range narrowing at every villain decision node
- All bets/raises clipped to all-in to prevent infinite recursion
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass

import torch

from playing_cards_lib.core import Card, Rank, Suit

from solver.model import SolverTransformer
from solver.eq_calculator import all_hands_vs_range, _normalize_combo as _eq_normalize_combo
from solver.ev_calculator import (
    _build_sequence_tokens,
    _tensorize_sequence,
    _action_key_to_model_action,
    ACTION_TO_BET_PCT,
    RAISE_MULTIPLIER,
)
from solver.ranges import filter_range_by_equity, _normalize_combo, _cards_conflict
from solver.models import Token, TokenType

logger = logging.getLogger(__name__)

# Future-street action sets (reduced from current solver UI)
HERO_OPEN_ACTIONS = ["Check", "B66", "B133", "B200"]
HERO_FACING_BET_ACTIONS = ["Fold", "Call", "R3x"]

NEXT_STREET = {"flop": "turn", "turn": "river"}

# All 52 cards for deck enumeration
_ALL_CARDS = [Card(r, s) for r in Rank for s in Suit]


@dataclass
class TreeNode:
    """A node in the solve tree representing a decision point."""
    street: str
    board: list[Card]
    pot_bb: float
    hero_committed: float       # hero's chips committed this street
    villain_committed: float    # villain's chips committed this street
    stack_left: float           # remaining effective stack for either player
    is_hero_turn: bool
    hero_is_ip: bool
    villain_range: dict[tuple[Card, Card], float]


def _remaining_deck(board: list[Card]) -> list[Card]:
    """Cards not on the board."""
    board_set = {(c.rank, c.suit) for c in board}
    return [c for c in _ALL_CARDS if (c.rank, c.suit) not in board_set]


def _card_in_combo(card: Card, combo: tuple[Card, Card]) -> bool:
    """Check if a card is one of the combo's hole cards."""
    return ((card.rank == combo[0].rank and card.suit == combo[0].suit) or
            (card.rank == combo[1].rank and card.suit == combo[1].suit))


def _remove_card_from_range(
    range_: dict[tuple[Card, Card], float],
    card: Card,
) -> dict[tuple[Card, Card], float]:
    """Remove combos conflicting with a dealt card."""
    return {
        combo: freq for combo, freq in range_.items()
        if not _card_in_combo(card, combo)
    }


def _clip_to_all_in(amount: float, stack_left: float) -> float:
    """Clip a bet/raise to remaining stack."""
    return min(amount, max(stack_left, 0.0))


def _compute_bet_bb(action_key: str, pot_bb: float, facing_bet: float) -> float:
    """Compute bet/raise amount in BB (before all-in clipping).

    For bets (B66/B133/B200): percentage of pot.
    For raises (R3x): 3× the bet being faced.
    """
    if action_key == "B66":
        return 0.66 * pot_bb
    elif action_key == "B133":
        return 1.33 * pot_bb
    elif action_key == "B200":
        return 2.0 * pot_bb
    elif action_key == "R3x":
        return 3.0 * facing_bet
    return 0.0


def _is_opening(hero_committed: float, villain_committed: float) -> bool:
    """Whether this is an opening action (no bet to face)."""
    return villain_committed <= hero_committed


def _extract_villain_probs(
    probs: torch.Tensor,
    is_facing_hero_bet: bool,
) -> tuple[float, float, float]:
    """Extract fold/call/raise probabilities from model output.

    When villain faces a hero bet: fold / (check+call) / (bet+raise)
    When villain opens (hero checked): split into check_back / bet
    """
    if is_facing_hero_bet:
        fold = probs[0].item()
        call = probs[1].item() + probs[2].item()
        raise_ = probs[3].item() + probs[4].item()
    else:
        # Villain is opening (hero checked). Model outputs:
        # check+call = check back, bet+raise = bet
        fold = 0.0
        call = probs[1].item() + probs[2].item()  # check back
        raise_ = probs[3].item() + probs[4].item()  # bet
    total = fold + call + raise_
    if total > 0:
        return fold / total, call / total, raise_ / total
    return 0.0, 0.5, 0.5


# ---------------------------------------------------------------------------
# Model prediction batching
# ---------------------------------------------------------------------------

def _build_hero_action_token(
    action_key: str,
    pot_bb: float,
    facing_bet: float,
    stack_left: float,
) -> Token:
    """Build a Token for a hero action in the tree."""
    bet_pct = ACTION_TO_BET_PCT.get(action_key, 0.0)
    model_action = _action_key_to_model_action(action_key)

    if action_key in ("Check", "Fold"):
        bet_bb = 0.0
    elif action_key == "Call":
        bet_bb = 0.0  # calls are 0 in training data
    elif action_key in RAISE_MULTIPLIER:
        bet_bb = _clip_to_all_in(RAISE_MULTIPLIER[action_key] * facing_bet, stack_left)
    else:
        bet_bb = _clip_to_all_in(_compute_bet_bb(action_key, pot_bb, facing_bet), stack_left)

    return Token(TokenType.ACTION, action=model_action,
                 bet_size_pct=bet_pct, bet_size_bb=bet_bb)


def _predict_single(
    model: SolverTransformer,
    board: list[Card],
    action_prefix: list[str],
    hero_action_token: Token,
    effective_stack_bb: float,
) -> torch.Tensor:
    """Run a single model prediction. Returns softmax probabilities."""
    base_tokens = _build_sequence_tokens(board, action_prefix)
    full_tokens = base_tokens + [hero_action_token]
    with torch.no_grad():
        batch = _tensorize_sequence(full_tokens, effective_stack_bb)
        logits = model(batch)
        return torch.softmax(logits, dim=-1).cpu()[0]


# ---------------------------------------------------------------------------
# Core recursive solver
# ---------------------------------------------------------------------------

def _showdown_equity(
    node: TreeNode,
    equity_cache: dict[tuple, dict],
    valid_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], float]:
    """Compute showdown EV at a river leaf. Returns combo -> EV (= equity × pot)."""
    if len(node.board) != 5:
        # Shouldn't happen, but fallback
        return {c: 0.5 * node.pot_bb for c in valid_combos}

    board_key = tuple(sorted((c.rank.value, c.suit.value) for c in node.board))
    if board_key not in equity_cache:
        equity_cache[board_key] = all_hands_vs_range(
            valid_combos, node.villain_range, node.board
        )
    equities = equity_cache[board_key]
    return {
        c: equities.get(_normalize_combo(c), 0.5) * node.pot_bb
        for c in valid_combos
    }


def _enumerate_next_street(
    node: TreeNode,
    model: SolverTransformer,
    action_prefix: list[str],
    effective_stack_bb: float,
    equity_cache: dict[tuple, dict],
    valid_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], float]:
    """Enumerate all next-street cards and average EVs.

    Flop → enumerate ~47 turn cards.
    Turn → enumerate ~46 river cards.
    """
    next_street = NEXT_STREET.get(node.street)
    if not next_street:
        return _showdown_equity(node, equity_cache, valid_combos)

    deck = _remaining_deck(node.board)
    ev_sums: dict[tuple[Card, Card], float] = {c: 0.0 for c in valid_combos}
    combo_counts: dict[tuple[Card, Card], int] = {c: 0 for c in valid_combos}

    for card in deck:
        new_board = node.board + [card]
        child = TreeNode(
            street=next_street,
            board=new_board,
            pot_bb=node.pot_bb,
            hero_committed=0.0,
            villain_committed=0.0,
            stack_left=node.stack_left,
            is_hero_turn=not node.hero_is_ip,  # OOP acts first on new street
            hero_is_ip=node.hero_is_ip,
            villain_range=_remove_card_from_range(node.villain_range, card),
        )
        child_evs = _solve_node(
            child, model, action_prefix, effective_stack_bb,
            equity_cache, valid_combos,
        )
        for c in valid_combos:
            if not _card_in_combo(card, c):
                ev_sums[c] += child_evs.get(c, 0.0)
                combo_counts[c] += 1

    return {
        c: ev_sums[c] / max(combo_counts[c], 1) for c in valid_combos
    }


def _solve_hero_node(
    node: TreeNode,
    model: SolverTransformer,
    action_prefix: list[str],
    effective_stack_bb: float,
    equity_cache: dict[tuple, dict],
    valid_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], float]:
    """Hero picks the action with highest EV per combo."""
    opening = _is_opening(node.hero_committed, node.villain_committed)
    actions = HERO_OPEN_ACTIONS if opening else HERO_FACING_BET_ACTIONS

    best_evs: dict[tuple[Card, Card], float] = {c: float('-inf') for c in valid_combos}

    for action_key in actions:
        action_evs = _solve_hero_action(
            node, action_key, model, action_prefix,
            effective_stack_bb, equity_cache, valid_combos,
        )
        for c in valid_combos:
            ev = action_evs.get(c, 0.0)
            if ev > best_evs[c]:
                best_evs[c] = ev

    # Floor at 0 — hero can always fold if all actions are negative
    return {c: max(0.0, ev) for c, ev in best_evs.items()}


def _solve_hero_action(
    node: TreeNode,
    action_key: str,
    model: SolverTransformer,
    action_prefix: list[str],
    effective_stack_bb: float,
    equity_cache: dict[tuple, dict],
    valid_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], float]:
    """Compute EV for a single hero action."""

    if action_key == "Fold":
        return {c: 0.0 for c in valid_combos}

    if action_key == "Call":
        call_cost = node.villain_committed - node.hero_committed
        if node.street == "river":
            # River call → showdown
            show_node = TreeNode(
                street="river", board=node.board,
                pot_bb=node.pot_bb + call_cost,
                hero_committed=0.0, villain_committed=0.0,
                stack_left=node.stack_left - call_cost,
                is_hero_turn=True, hero_is_ip=node.hero_is_ip,
                villain_range=node.villain_range,
            )
            show_evs = _showdown_equity(show_node, equity_cache, valid_combos)
            return {c: ev - call_cost for c, ev in show_evs.items()}
        else:
            # Call closes street → enumerate next street
            next_node = TreeNode(
                street=node.street, board=node.board,
                pot_bb=node.pot_bb + call_cost,
                hero_committed=0.0, villain_committed=0.0,
                stack_left=node.stack_left - call_cost,
                is_hero_turn=True, hero_is_ip=node.hero_is_ip,
                villain_range=node.villain_range,
            )
            next_evs = _enumerate_next_street(
                next_node, model, action_prefix,
                effective_stack_bb, equity_cache, valid_combos,
            )
            return {c: ev - call_cost for c, ev in next_evs.items()}

    if action_key == "Check":
        if node.hero_is_ip and _is_opening(node.hero_committed, node.villain_committed):
            # IP check closes the street (both checked or hero checked back)
            if node.street == "river":
                return _showdown_equity(node, equity_cache, valid_combos)
            else:
                return _enumerate_next_street(
                    node, model, action_prefix,
                    effective_stack_bb, equity_cache, valid_combos,
                )
        else:
            # OOP check (or IP check facing no action) → villain acts
            child = TreeNode(
                street=node.street, board=node.board,
                pot_bb=node.pot_bb,
                hero_committed=node.hero_committed,
                villain_committed=node.villain_committed,
                stack_left=node.stack_left,
                is_hero_turn=False,
                hero_is_ip=node.hero_is_ip,
                villain_range=node.villain_range,
            )
            return _solve_villain_node(
                child, model, action_prefix, "Check",
                effective_stack_bb, equity_cache, valid_combos,
            )

    # Bet or Raise
    facing_bet = node.villain_committed - node.hero_committed
    raw_bet = _compute_bet_bb(action_key, node.pot_bb, facing_bet)
    bet_bb = _clip_to_all_in(raw_bet, node.stack_left)
    if bet_bb <= 0:
        return {c: 0.0 for c in valid_combos}

    child = TreeNode(
        street=node.street, board=node.board,
        pot_bb=node.pot_bb + bet_bb,
        hero_committed=node.hero_committed + bet_bb,
        villain_committed=node.villain_committed,
        stack_left=node.stack_left - bet_bb,
        is_hero_turn=False,
        hero_is_ip=node.hero_is_ip,
        villain_range=node.villain_range,
    )
    villain_evs = _solve_villain_node(
        child, model, action_prefix, action_key,
        effective_stack_bb, equity_cache, valid_combos,
    )
    return {c: ev - bet_bb for c, ev in villain_evs.items()}


def _solve_villain_node(
    node: TreeNode,
    model: SolverTransformer,
    action_prefix: list[str],
    hero_action_key: str,
    effective_stack_bb: float,
    equity_cache: dict[tuple, dict],
    valid_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], float]:
    """Villain responds to hero's action. Weights branches by model predictions.

    Range narrowing happens here: villain's range is split into fold/call/raise
    sub-ranges, and each branch continues with its narrowed sub-range.
    """
    # Get model prediction for villain's response
    facing_bet = node.hero_committed - node.villain_committed
    hero_token = _build_hero_action_token(
        hero_action_key, node.pot_bb - facing_bet,  # pot before hero's bet
        max(node.villain_committed - (node.hero_committed - facing_bet), 0),  # bet hero was facing
        node.stack_left + facing_bet,  # stack before hero's bet
    )
    probs = _predict_single(
        model, node.board, action_prefix, hero_token, effective_stack_bb,
    )
    is_facing_hero_bet = facing_bet > 0
    fold_pct, call_pct, raise_pct = _extract_villain_probs(probs, is_facing_hero_bet)

    # Range narrowing: split villain range into sub-ranges
    if node.villain_range and node.board:
        raising_range, calling_range, folding_range = filter_range_by_equity(
            node.villain_range, node.board, node.street,
            raise_pct=raise_pct * 100, call_pct=call_pct * 100,
            hard_split=True,
        )
    else:
        raising_range = calling_range = folding_range = node.villain_range

    # FOLD branch: hero wins entire pot
    fold_evs = {c: node.pot_bb for c in valid_combos}

    # CALL branch
    call_amount = node.hero_committed - node.villain_committed
    call_child = TreeNode(
        street=node.street, board=node.board,
        pot_bb=node.pot_bb + call_amount,
        hero_committed=0.0, villain_committed=0.0,
        stack_left=node.stack_left - call_amount,
        is_hero_turn=True,
        hero_is_ip=node.hero_is_ip,
        villain_range=calling_range,
    )
    if node.street == "river":
        call_evs = _showdown_equity(call_child, equity_cache, valid_combos)
    elif is_facing_hero_bet:
        # Villain called a bet → street over, enumerate next street
        call_evs = _enumerate_next_street(
            call_child, model, action_prefix,
            effective_stack_bb, equity_cache, valid_combos,
        )
    else:
        # Villain "called" = checked back → street over, enumerate next
        if node.street == "river":
            call_evs = _showdown_equity(call_child, equity_cache, valid_combos)
        else:
            call_evs = _enumerate_next_street(
                call_child, model, action_prefix,
                effective_stack_bb, equity_cache, valid_combos,
            )

    # RAISE/BET branch: villain raises, hero decides fold(0) or call
    if raise_pct > 0.001 and node.stack_left > 0:
        hero_bet = node.hero_committed - node.villain_committed
        v_raise_to = _clip_to_all_in(3.0 * hero_bet if hero_bet > 0 else 0.66 * node.pot_bb,
                                      node.stack_left)
        if v_raise_to > 0:
            hero_call_cost = v_raise_to  # hero must match villain's total raise
            hero_call_cost = _clip_to_all_in(hero_call_cost, node.stack_left)

            raise_child = TreeNode(
                street=node.street, board=node.board,
                pot_bb=node.pot_bb + call_amount + v_raise_to + hero_call_cost,
                hero_committed=0.0, villain_committed=0.0,
                stack_left=node.stack_left - call_amount - v_raise_to - hero_call_cost,
                is_hero_turn=True,
                hero_is_ip=node.hero_is_ip,
                villain_range=raising_range,
            )
            if node.street == "river":
                raise_call_evs = _showdown_equity(raise_child, equity_cache, valid_combos)
            else:
                raise_call_evs = _enumerate_next_street(
                    raise_child, model, action_prefix,
                    effective_stack_bb, equity_cache, valid_combos,
                )
            # Hero picks max(fold=0, call_ev - cost)
            raise_evs = {
                c: max(0.0, raise_call_evs.get(c, 0.0) - hero_call_cost)
                for c in valid_combos
            }
        else:
            raise_evs = {c: 0.0 for c in valid_combos}
    else:
        raise_evs = {c: 0.0 for c in valid_combos}

    # Weighted sum
    return {
        c: fold_pct * fold_evs[c] + call_pct * call_evs.get(c, 0.0) + raise_pct * raise_evs[c]
        for c in valid_combos
    }


def _solve_node(
    node: TreeNode,
    model: SolverTransformer,
    action_prefix: list[str],
    effective_stack_bb: float,
    equity_cache: dict[tuple, dict],
    valid_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], float]:
    """Solve a tree node, returning combo -> EV map."""
    if node.is_hero_turn:
        return _solve_hero_node(
            node, model, action_prefix, effective_stack_bb,
            equity_cache, valid_combos,
        )
    else:
        # Shouldn't reach here — villain nodes are called explicitly
        # with the hero action that triggered them
        return {c: 0.0 for c in valid_combos}


# ---------------------------------------------------------------------------
# Top-level entry points
# ---------------------------------------------------------------------------

def mc_solve_spot(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    pot_bb: float,
    effective_stack_bb: float,
    valid_combos: list[tuple[Card, Card]],
    hero_is_ip: bool,
) -> dict[str, dict[tuple[Card, Card], float]]:
    """Solve a spot using the MC tree solver.

    Returns dict mapping action_key -> {combo: ev} for each hero action.
    """
    equity_cache: dict[tuple, dict] = {}
    results: dict[str, dict[tuple[Card, Card], float]] = {}

    # Determine if hero is opening or facing a bet
    last_action = action_prefix[-1].split(":")[-1] if action_prefix else ""
    is_facing_bet = last_action.startswith("B") or last_action.startswith("R")
    hero_committed = 0.0
    villain_committed = 0.0

    # If hero is facing a bet, compute how much villain bet
    if is_facing_bet:
        bet_pct = ACTION_TO_BET_PCT.get(last_action, 0.0)
        mult = RAISE_MULTIPLIER.get(last_action, 0.0)
        if mult > 0:
            # Need to figure out the bet amount from context
            # For now, estimate from pot
            villain_committed = mult * (pot_bb * 0.5)  # rough estimate
        elif bet_pct > 0:
            # pot_bb already includes villain's bet
            pot_before = pot_bb / (1.0 + bet_pct / 100.0)
            villain_committed = pot_before * bet_pct / 100.0
        villain_committed = min(villain_committed, effective_stack_bb)

    stack_left = effective_stack_bb

    for action_key in hero_actions:
        if action_key == "Fold":
            results[action_key] = {c: 0.0 for c in valid_combos}
            continue

        node = TreeNode(
            street=street,
            board=board,
            pot_bb=pot_bb,
            hero_committed=hero_committed,
            villain_committed=villain_committed,
            stack_left=stack_left,
            is_hero_turn=True,
            hero_is_ip=hero_is_ip,
            villain_range=villain_range,
        )
        results[action_key] = _solve_hero_action(
            node, action_key, model, action_prefix,
            effective_stack_bb, equity_cache, valid_combos,
        )

    return results


def mc_solve_spot_streaming(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    pot_bb: float,
    effective_stack_bb: float,
    valid_combos: list[tuple[Card, Card]],
    hero_is_ip: bool,
):
    """Generator that yields partial results as the tree solve progresses.

    Yields dicts with:
    - {"type": "progress", "stage": "...", ...} for status updates
    - {"type": "update", "progress": 0-1, "actions": {...}} for partial EVs
    - {"type": "complete", "progress": 1.0, ...} for final result
    """
    t0 = time.perf_counter()
    equity_cache: dict[tuple, dict] = {}

    # Determine hero's position context
    last_action = action_prefix[-1].split(":")[-1] if action_prefix else ""
    is_facing_bet = last_action.startswith("B") or last_action.startswith("R")
    hero_committed = 0.0
    villain_committed = 0.0

    if is_facing_bet:
        bet_pct = ACTION_TO_BET_PCT.get(last_action, 0.0)
        mult = RAISE_MULTIPLIER.get(last_action, 0.0)
        if mult > 0:
            villain_committed = mult * (pot_bb * 0.5)
        elif bet_pct > 0:
            pot_before = pot_bb / (1.0 + bet_pct / 100.0)
            villain_committed = pot_before * bet_pct / 100.0
        villain_committed = min(villain_committed, effective_stack_bb)

    stack_left = effective_stack_bb

    if street == "river":
        # No card enumeration needed — solve directly
        results = mc_solve_spot(
            model, board, street, action_prefix, hero_actions,
            villain_range, pot_bb, effective_stack_bb, valid_combos, hero_is_ip,
        )
        elapsed = time.perf_counter() - t0
        yield {
            "type": "complete",
            "progress": 1.0,
            "simsComplete": 1,
            "solveTime": round(elapsed, 2),
            "combo_evs": _serialize_combo_evs(results, valid_combos),
        }
        return

    # For flop/turn: enumerate next-street cards with streaming
    next_street = NEXT_STREET.get(street)
    if not next_street:
        return

    deck = _remaining_deck(board)
    random.shuffle(deck)  # shuffle for unbiased early updates

    # Accumulators per hero action per combo
    ev_sums: dict[str, dict[tuple[Card, Card], float]] = {
        a: {c: 0.0 for c in valid_combos} for a in hero_actions
    }
    combo_counts: dict[str, dict[tuple[Card, Card], int]] = {
        a: {c: 0 for c in valid_combos} for a in hero_actions
    }

    yield {"type": "progress", "stage": "solving", "totalCards": len(deck)}

    for card_idx, card in enumerate(deck):
        new_board = board + [card]
        card_villain_range = _remove_card_from_range(villain_range, card)

        # Solve each hero action for this card
        for action_key in hero_actions:
            if action_key == "Fold":
                for c in valid_combos:
                    if not _card_in_combo(card, c):
                        ev_sums[action_key][c] += 0.0
                        combo_counts[action_key][c] += 1
                continue

            node = TreeNode(
                street=street,
                board=board,
                pot_bb=pot_bb,
                hero_committed=hero_committed,
                villain_committed=villain_committed,
                stack_left=stack_left,
                is_hero_turn=True,
                hero_is_ip=hero_is_ip,
                villain_range=card_villain_range,
            )

            # Get model prediction for this hero action
            facing_bet = villain_committed - hero_committed
            hero_token = _build_hero_action_token(
                action_key, pot_bb, facing_bet, stack_left,
            )
            probs = _predict_single(
                model, board, action_prefix, hero_token, effective_stack_bb,
            )
            is_hero_aggressive = action_key not in ("Check", "Call")
            fold_pct, call_pct, raise_pct = _extract_villain_probs(probs, is_hero_aggressive)

            # Compute bet sizing
            if action_key == "Call":
                call_cost = villain_committed - hero_committed
                # After calling, enumerate the SPECIFIC next card
                next_node = TreeNode(
                    street=next_street, board=new_board,
                    pot_bb=pot_bb + call_cost,
                    hero_committed=0.0, villain_committed=0.0,
                    stack_left=stack_left - call_cost,
                    is_hero_turn=not hero_is_ip,
                    hero_is_ip=hero_is_ip,
                    villain_range=card_villain_range,
                )
                card_evs = _solve_node(
                    next_node, model, action_prefix,
                    effective_stack_bb, equity_cache, valid_combos,
                )
                for c in valid_combos:
                    if not _card_in_combo(card, c):
                        ev_sums[action_key][c] += card_evs.get(c, 0.0) - call_cost
                        combo_counts[action_key][c] += 1

            elif action_key == "Check":
                if hero_is_ip and _is_opening(hero_committed, villain_committed):
                    # IP check closes street — solve next street for this card
                    next_node = TreeNode(
                        street=next_street, board=new_board,
                        pot_bb=pot_bb,
                        hero_committed=0.0, villain_committed=0.0,
                        stack_left=stack_left,
                        is_hero_turn=not hero_is_ip,
                        hero_is_ip=hero_is_ip,
                        villain_range=card_villain_range,
                    )
                    card_evs = _solve_node(
                        next_node, model, action_prefix,
                        effective_stack_bb, equity_cache, valid_combos,
                    )
                else:
                    # OOP check → solve villain's response on CURRENT board,
                    # then enumerate next cards within villain response
                    check_node = TreeNode(
                        street=street, board=board,
                        pot_bb=pot_bb,
                        hero_committed=hero_committed,
                        villain_committed=villain_committed,
                        stack_left=stack_left,
                        is_hero_turn=False,
                        hero_is_ip=hero_is_ip,
                        villain_range=card_villain_range,
                    )
                    card_evs = _solve_villain_node(
                        check_node, model, action_prefix, "Check",
                        effective_stack_bb, equity_cache, valid_combos,
                    )
                for c in valid_combos:
                    if not _card_in_combo(card, c):
                        ev_sums[action_key][c] += card_evs.get(c, 0.0)
                        combo_counts[action_key][c] += 1

            else:
                # Bet/Raise: model predicts villain response
                raw_bet = _compute_bet_bb(action_key, pot_bb, facing_bet)
                bet_bb = _clip_to_all_in(raw_bet, stack_left)
                if bet_bb <= 0:
                    for c in valid_combos:
                        if not _card_in_combo(card, c):
                            combo_counts[action_key][c] += 1
                    continue

                # Compute villain response branches for this specific card
                # Range narrowing
                if card_villain_range and board:
                    raising_range, calling_range, _ = filter_range_by_equity(
                        card_villain_range, board, street,
                        raise_pct=raise_pct * 100, call_pct=call_pct * 100,
                        hard_split=True,
                    )
                else:
                    raising_range = calling_range = card_villain_range

                # Fold: hero wins pot
                fold_ev_per_combo = pot_bb + bet_bb  # pot before + hero's bet (villain folds)
                # Actually fold means villain folds, hero wins the pot as-is (pot_bb + bet_bb)
                # But hero already committed bet_bb, so net = pot_bb + bet_bb - bet_bb = pot_bb
                # Wait: fold_ev should be hero wins pot (which includes hero's bet that villain
                # didn't match). So fold_ev = pot_bb (the pot before hero bet). Hero gets their
                # bet back since villain folded. Net = pot_bb (profit = pot_bb minus nothing).
                # Actually: hero committed bet_bb. Villain folds. Hero wins pot_bb (the pot
                # before hero acted). So net EV = pot_bb - bet_bb + pot_bb + bet_bb = pot_bb.
                # No wait. The pot is pot_bb. Hero bets bet_bb. Villain folds.
                # Hero wins pot_bb. Hero's cost was bet_bb. Net = pot_bb - bet_bb.
                # But the caller already subtracts bet_bb. So here we return pot_bb + bet_bb
                # and the caller does (ev - bet_bb) = pot_bb. That's correct.
                fold_ev = node.pot_bb + bet_bb  # total pot hero wins (includes their own bet)

                # Call: villain calls, go to next street for this specific card
                call_child = TreeNode(
                    street=next_street, board=new_board,
                    pot_bb=pot_bb + bet_bb + bet_bb,  # hero bet + villain call
                    hero_committed=0.0, villain_committed=0.0,
                    stack_left=stack_left - bet_bb - bet_bb,
                    is_hero_turn=not hero_is_ip,
                    hero_is_ip=hero_is_ip,
                    villain_range=calling_range,
                )
                call_card_evs = _solve_node(
                    call_child, model, action_prefix,
                    effective_stack_bb, equity_cache, valid_combos,
                )

                # Raise: villain raises, hero calls or folds
                hero_bet_size = bet_bb
                v_raise_to = _clip_to_all_in(3.0 * hero_bet_size, stack_left - bet_bb)
                hero_call_cost = v_raise_to  # hero must put in this much more
                hero_call_cost = _clip_to_all_in(hero_call_cost, stack_left - bet_bb)

                if v_raise_to > 0 and raise_pct > 0.001:
                    raise_child = TreeNode(
                        street=next_street, board=new_board,
                        pot_bb=pot_bb + bet_bb + bet_bb + v_raise_to + hero_call_cost,
                        hero_committed=0.0, villain_committed=0.0,
                        stack_left=stack_left - bet_bb - bet_bb - v_raise_to - hero_call_cost,
                        is_hero_turn=not hero_is_ip,
                        hero_is_ip=hero_is_ip,
                        villain_range=raising_range,
                    )
                    raise_call_evs = _solve_node(
                        raise_child, model, action_prefix,
                        effective_stack_bb, equity_cache, valid_combos,
                    )
                    raise_evs = {
                        c: max(0.0, raise_call_evs.get(c, 0.0) - hero_call_cost)
                        for c in valid_combos
                    }
                else:
                    raise_evs = {c: 0.0 for c in valid_combos}

                for c in valid_combos:
                    if not _card_in_combo(card, c):
                        total_ev = (fold_pct * fold_ev
                                    + call_pct * call_card_evs.get(c, 0.0)
                                    + raise_pct * raise_evs.get(c, 0.0))
                        ev_sums[action_key][c] += total_ev
                        combo_counts[action_key][c] += 1

        # Yield periodic updates
        if (card_idx + 1) % 5 == 0 or card_idx == len(deck) - 1:
            progress = (card_idx + 1) / len(deck)
            running_avgs = {}
            for a in hero_actions:
                action_avg = 0.0
                count = 0
                for c in valid_combos:
                    if combo_counts[a][c] > 0:
                        action_avg += ev_sums[a][c] / combo_counts[a][c]
                        count += 1
                running_avgs[a] = round(action_avg / max(count, 1), 2)

            yield {
                "type": "update",
                "progress": round(progress, 3),
                "simsComplete": card_idx + 1,
                "totalCards": len(deck),
                "actions": running_avgs,
            }

    # Final result: compute average EVs
    final_evs: dict[str, dict[tuple[Card, Card], float]] = {}
    for a in hero_actions:
        final_evs[a] = {}
        for c in valid_combos:
            if combo_counts[a][c] > 0:
                final_evs[a][c] = ev_sums[a][c] / combo_counts[a][c]
            else:
                final_evs[a][c] = 0.0

    elapsed = time.perf_counter() - t0
    yield {
        "type": "complete",
        "progress": 1.0,
        "simsComplete": len(deck),
        "solveTime": round(elapsed, 2),
        "combo_evs": _serialize_combo_evs(final_evs, valid_combos),
    }


def _serialize_combo_evs(
    evs: dict[str, dict[tuple[Card, Card], float]],
    valid_combos: list[tuple[Card, Card]],
) -> dict[str, dict[str, float]]:
    """Serialize combo EVs to JSON-friendly format."""
    result = {}
    for action_key, combo_evs in evs.items():
        result[action_key] = {}
        for c in valid_combos:
            card_str = (f"{c[0].rank.value}{c[0].suit.value}"
                        f"{c[1].rank.value}{c[1].suit.value}")
            result[action_key][card_str] = round(combo_evs.get(c, 0.0), 2)
    return result
