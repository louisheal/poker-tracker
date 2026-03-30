"""Solver EV calculator -- computes expected value for each hero hand
at a decision point using the trained model's villain response predictions.

Different from app/parsers/ev_calculator.py which uses empirical data.
This version uses the transformer model to predict villain behavior.
"""

from __future__ import annotations

import torch

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards
from app.models.enums import Action
from app.parsers.hand_types import classify_made_hand, classify_flush_draw, classify_straight_draw
from app.parsers.equity import get_equity, HandTriple

from solver.model import SolverTransformer
from solver.models import Token, TokenType
from solver.dataset import (
    MAX_SEQ_LEN,
    RANK_TO_INDEX, SUIT_TO_INDEX, ACTION_TO_INDEX,
)
from solver.ranges import (
    get_starting_range,
    compute_hand_equity,
    filter_range_by_equity,
    _hand_key_to_combos,
    _cards_conflict,
)


RANKS = list(Rank)
SUITS = list(Suit)

# Hero action set matching frontend types.ts
HERO_ACTIONS_PREFLOP = ["Fold", "Call", "Raise"]
HERO_ACTIONS_OPEN = ["Check", "B33", "B50", "B66", "B100", "B133", "B200"]
HERO_ACTIONS_FACING_BET = ["Fold", "Call", "R3x", "R4x", "R5x"]

ACTION_TO_BET_PCT: dict[str, float] = {
    "Check": 0.0,
    "Fold": 0.0,
    "Call": 0.0,
    "Raise": 300.0,  # Preflop raise ~3x
    "B33": 33.0,
    "B50": 50.0,
    "B66": 66.0,
    "B100": 100.0,
    "B133": 133.0,
    "B200": 200.0,
    "R3x": 300.0,
    "R4x": 400.0,
    "R5x": 500.0,
}


def _detect_street(board: list[Card]) -> str:
    if len(board) <= 3:
        return "flop"
    if len(board) == 4:
        return "turn"
    return "river"


def _action_key_to_model_action(action_key: str) -> int:
    """Map a hero action key to the model's action index."""
    mapping = {
        "Fold": ACTION_TO_INDEX[Action.FOLD],
        "Check": ACTION_TO_INDEX[Action.CHECK],
        "Call": ACTION_TO_INDEX[Action.CALL],
        "Raise": ACTION_TO_INDEX[Action.RAISE],
    }
    if action_key in mapping:
        return mapping[action_key]
    if action_key.startswith("B"):
        return ACTION_TO_INDEX[Action.BET]
    if action_key.startswith("R"):
        return ACTION_TO_INDEX[Action.RAISE]
    return ACTION_TO_INDEX[Action.CHECK]


def _build_sequence_tokens(
    board: list[Card],
    action_prefix: list[str],
) -> list[Token]:
    """Build the token sequence up to the current decision point.

    Includes preflop-style action prefix tokens followed by board cards
    with street markers. No hole cards -- model only sees actions + board.
    """
    tokens: list[Token] = []

    # Action prefix tokens (preflop actions + any postflop actions already taken)
    for action_str in action_prefix:
        # Parse "POS:ACTION" format from frontend
        parts = action_str.split(":")
        action_key = parts[-1] if len(parts) > 1 else parts[0]
        bet_pct = ACTION_TO_BET_PCT.get(action_key, 0.0)
        model_action = _action_key_to_model_action(action_key)
        tokens.append(Token(TokenType.ACTION, action=model_action, bet_size_pct=bet_pct))

    # Board cards with street markers
    if len(board) >= 3:
        tokens.append(Token(TokenType.STREET_MARKER, action=0))  # FLOP
        for card in board[:3]:
            tokens.append(Token(TokenType.CARD, rank=RANK_TO_INDEX[card.rank], suit=SUIT_TO_INDEX[card.suit]))

    if len(board) >= 4:
        tokens.append(Token(TokenType.STREET_MARKER, action=1))  # TURN
        tokens.append(Token(TokenType.CARD, rank=RANK_TO_INDEX[board[3].rank], suit=SUIT_TO_INDEX[board[3].suit]))

    if len(board) >= 5:
        tokens.append(Token(TokenType.STREET_MARKER, action=2))  # RIVER
        tokens.append(Token(TokenType.CARD, rank=RANK_TO_INDEX[board[4].rank], suit=SUIT_TO_INDEX[board[4].suit]))

    return tokens


def _tensorize_sequence(tokens: list[Token]) -> dict[str, torch.Tensor]:
    """Convert a token list to a batch-of-1 tensor dict for the model."""
    seq = tokens[:MAX_SEQ_LEN]
    length = len(seq)

    token_types = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    ranks = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    suits = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    actions = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    bet_sizes = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.float)
    street_ids = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    padding_mask = torch.ones(1, MAX_SEQ_LEN, dtype=torch.bool)

    for i, tok in enumerate(seq):
        token_types[0, i] = int(tok.token_type)
        ranks[0, i] = tok.rank
        suits[0, i] = tok.suit
        actions[0, i] = tok.action
        bet_sizes[0, i] = tok.bet_size_pct
        street_ids[0, i] = tok.action if tok.token_type == TokenType.STREET_MARKER else 0
        padding_mask[0, i] = False

    return {
        "token_types": token_types,
        "ranks": ranks,
        "suits": suits,
        "actions": actions,
        "bet_sizes": bet_sizes,
        "street_ids": street_ids,
        "padding_mask": padding_mask,
    }


def _generate_hand_keys() -> list[str]:
    """Generate all 169 canonical hand keys."""
    rank_chars = "A K Q J T 9 8 7 6 5 4 3 2".split()
    keys = []
    for i, r1 in enumerate(rank_chars):
        for j, r2 in enumerate(rank_chars):
            if i == j:
                keys.append(f"{r1}{r2}")
            elif i < j:
                keys.append(f"{r1}{r2}s")
            else:
                keys.append(f"{r2}{r1}o")
    return keys


ALL_HAND_KEYS = _generate_hand_keys()


def _classify_hand(hole: tuple[Card, Card], board: list[Card]) -> HandTriple:
    hc = HoleCards(hole[0], hole[1])
    made = classify_made_hand(hc, board)
    fd = classify_flush_draw(hc, board)
    sd = classify_straight_draw(hc, board)
    return (made, fd, sd)


def solve_spot(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_position: str,
    villain_position: str,
    pot_type: str,
    pot_bb: float,
    hero_actions: list[str],
) -> dict:
    """Run the solver for a single spot.

    For each hero action, uses the model to predict villain's response,
    then computes EV using equity vs the calling range.

    Returns a SolverResult dict with:
      - hands: per-hand best action + EVs + combo details
      - actions: per-action summary (avg EV, count)
      - totalHands: number of hands evaluated
    """
    villain_range = get_starting_range(villain_position, pot_type)

    hands: dict[str, dict] = {}
    action_summaries: dict[str, dict] = {}

    for action_key in hero_actions:
        bet_pct = ACTION_TO_BET_PCT.get(action_key, 0.0)
        bet_bb = (bet_pct / 100.0) * pot_bb

        # Build sequence without hole cards (model only sees actions + board)
        base_tokens = _build_sequence_tokens(board, action_prefix)

        # Add hero's action token
        model_action = _action_key_to_model_action(action_key)
        hero_token = Token(TokenType.ACTION, action=model_action, bet_size_pct=bet_pct)
        full_tokens = base_tokens + [hero_token]

        # Run model
        with torch.no_grad():
            batch = _tensorize_sequence(full_tokens)
            logits = model(batch)
            probs = torch.softmax(logits, dim=-1).cpu()[0]

        # Model outputs: F=0, X=1, C=2, B=3, R=4
        fold_pct = probs[0].item()
        call_pct = probs[2].item() + probs[1].item()  # Check + Call = passive
        raise_pct = probs[3].item() + probs[4].item()  # Bet + Raise = aggressive

        # Normalize to sum to 1
        total = fold_pct + call_pct + raise_pct
        if total > 0:
            fold_pct /= total
            call_pct /= total
            raise_pct /= total

        # Filter villain range into sub-ranges (skip for preflop -- no board for equity)
        if street == "preflop" or not board:
            calling_range = villain_range
        else:
            calling_range, raising_range, folding_range = filter_range_by_equity(
                villain_range, board, street,
                raise_pct=raise_pct * 100,
                call_pct=call_pct * 100,
            )

        ev_sum = 0.0
        hand_count = 0

        for hand_key in ALL_HAND_KEYS:
            combos = _hand_key_to_combos(hand_key)
            valid_combo = None
            for combo in combos:
                if not _cards_conflict(combo, board):
                    valid_combo = combo
                    break
            if valid_combo is None:
                continue

            # EV vs calling range
            if street == "preflop" or not board:
                eq_vs_callers = 0.5  # No equity calc for preflop
            else:
                hero_triple = _classify_hand(valid_combo, board)
                eq_vs_callers = compute_hand_equity(hero_triple, calling_range, board, street) if calling_range else 0.5

            # EV calculation
            if action_key in ("Fold",):
                ev = 0.0  # Folding = 0 EV (already invested)
            elif action_key in ("Check",):
                ev = eq_vs_callers * pot_bb
            elif action_key in ("Call",):
                ev = eq_vs_callers * pot_bb - bet_bb * (1 - eq_vs_callers)
            else:
                # Bet/Raise: villain folds (win pot), calls (showdown), raises (lose bet)
                ev = (
                    fold_pct * pot_bb
                    + call_pct * (eq_vs_callers * (pot_bb + 2 * bet_bb) - bet_bb)
                    + raise_pct * (-bet_bb)
                )

            ev = round(ev, 2)

            if hand_key not in hands:
                hands[hand_key] = {"evs": {}, "bestAction": "", "combos": []}
            hands[hand_key]["evs"][action_key] = ev
            ev_sum += ev
            hand_count += 1

        action_summaries[action_key] = {
            "avgEv": round(ev_sum / max(hand_count, 1), 2),
            "bestActionCount": 0,
        }

    # Determine best action per hand
    for hand_key, data in hands.items():
        if data["evs"]:
            data["bestAction"] = max(data["evs"], key=lambda k: data["evs"][k])

    # Count best actions
    for data in hands.values():
        best = data["bestAction"]
        if best in action_summaries:
            action_summaries[best]["bestActionCount"] += 1

    # Generate combo-level details for each hand
    for hand_key, data in hands.items():
        combos_list = _hand_key_to_combos(hand_key)
        combo_results = []
        for combo in combos_list:
            if _cards_conflict(combo, board):
                continue
            card_str = f"{combo[0].rank.value}{combo[0].suit.value}{combo[1].rank.value}{combo[1].suit.value}"
            combo_results.append({
                "combo": card_str,
                "bestAction": data["bestAction"],
                "evs": dict(data["evs"]),
            })
        data["combos"] = combo_results

    return {
        "hands": hands,
        "actions": action_summaries,
        "totalHands": len(hands),
    }
