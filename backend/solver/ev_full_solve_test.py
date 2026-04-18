"""Recursive river solver — full tree enumeration with batch model inference.

Two phases:
  1. Enumerate game tree → batch predict all villain response nodes → fill prediction cache.
  2. Recurse through tree computing EV with O(1) cache lookups + hand ranking comparisons.

River only for now; turn/flop fall back to mc_solver.
"""
from __future__ import annotations

import logging
from typing import Generator

import eval7
import numpy as np
import torch

from playing_cards_lib.core import Card

from solver.model import SolverTransformer
from solver.ev_calculator import (
    _build_sequence_tokens,
    _action_key_to_model_action,
)
from solver.eq_calculator import (
    _card_to_eval7,
    _cards_conflict_with_board,
    _normalize_combo,
)
from solver.mc_solver import (
    _batch_predict,
    _hero_token,
    _compute_facing_bet,
    _serialize,
    mc_solve_spot,
    mc_solve_spot_streaming,
)
from solver.ranges import filter_range_by_equity
from solver.models import Token, TokenType

logger = logging.getLogger(__name__)

VILLAIN_BET_FRACTION = 0.66
VILLAIN_RAISE_MULTIPLIER = 3.0
HERO_BET_FRACTIONS: dict[str, float] = {
    "B33": 0.33, "B66": 0.66, "B133": 1.33, "B200": 2.00,
}


def _compute_bet_size(
    action: str, pot: float, facing_bet: float, remaining_bb: float,
) -> float:
    """Hero's bet/raise size in BB, clipped to remaining_bb."""
    if action in ("Check", "Fold"):
        return 0.0
    if action == "Call":
        return min(facing_bet, remaining_bb)
    if action == "R3x":
        return min(3.0 * facing_bet, remaining_bb)
    if action in HERO_BET_FRACTIONS:
        return min(HERO_BET_FRACTIONS[action] * pot, remaining_bb)
    return 0.0


def _get_hero_actions(
    pot: float, facing_bet: float, remaining_bb: float, is_opener: bool,
) -> list[str]:
    """Available hero actions with all-in clipping."""
    if facing_bet == 0:
        actions = ["Check"]
        all_in_added = False
        for name in ("B33", "B66", "B133", "B200"):
            size = HERO_BET_FRACTIONS[name] * pot
            if size >= remaining_bb:
                if not all_in_added:
                    actions.append(name)
                    all_in_added = True
            else:
                actions.append(name)
        return actions

    if facing_bet >= remaining_bb - 1e-9:
        return ["Fold", "Call"]
    return ["Fold", "Call", "R3x"]


def _villain_response(
    probs: torch.Tensor, is_facing_aggression: bool, is_all_in: bool,
) -> tuple[float, float, float]:
    """Collapse 5-class model output [F, X, C, B, R] to (fold, passive, aggressive).
    Normalized to sum=1.

    Only uses legal action outputs per context:
      - Not facing aggression (hero checked): legal = X, B → group X+C, B+R
      - Facing aggression (hero bet/raised): legal = F, C, R → strict F, C, R
      - Facing all-in: legal = F, C → strict F, C
    """
    if is_all_in:
        fold_pct = probs[0].item()
        passive_pct = probs[2].item()
        aggressive_pct = 0.0
    elif is_facing_aggression:
        fold_pct = probs[0].item()
        passive_pct = probs[2].item()
        aggressive_pct = probs[4].item()
    else:
        fold_pct = 0.0
        passive_pct = probs[1].item() + probs[2].item()
        aggressive_pct = probs[3].item() + probs[4].item()
    total = fold_pct + passive_pct + aggressive_pct
    if total > 0:
        return fold_pct / total, passive_pct / total, aggressive_pct / total
    logger.warning("_villain_response: all probabilities summed to 0")
    return 0.0, 0.5, 0.5


def _action_to_cache_token(action: str) -> str:
    if action == "Check":
        return "X"
    return action


def _make_cache_key(prefix: str, token: str) -> str:
    return f"{prefix}>{token}" if prefix else token


def _all_in_token(
    pot: float, facing_bet: float, remaining_bb: float, is_opener: bool,
) -> Token:
    if is_opener:
        model_action = _action_key_to_model_action("B200")
        pct = (remaining_bb / pot * 100) if pot > 0 else 200.0
    else:
        model_action = _action_key_to_model_action("R3x")
        pct = (remaining_bb / facing_bet * 100) if facing_bet > 0 else 300.0
    return Token(
        TokenType.ACTION, action=model_action,
        bet_size_pct=pct, bet_size_bb=remaining_bb,
    )

def _enumerate_sequences(
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    cache_key_prefix: str,
    is_opener: bool,
    tokens_so_far: list[Token],
) -> list[tuple[str, bool, bool, list[Token]]]:
    """Walk game tree, collect all villain response nodes.

    Returns list of (cache_key, is_facing_aggression, is_all_in, token_list).
    Recursion terminates naturally when hero goes all-in (remaining_bb exhausted).
    """
    sequences: list[tuple[str, bool, bool, list[Token]]] = []
    hero_actions = _get_hero_actions(pot, facing_bet, remaining_bb, is_opener)

    for action in hero_actions:
        if action in ("Fold", "Call"):
            continue
        if action == "Check" and not is_opener:
            continue

        hero_bet = _compute_bet_size(action, pot, facing_bet, remaining_bb)
        token_str = _action_to_cache_token(action)
        cache_key = _make_cache_key(cache_key_prefix, token_str)
        is_facing_aggression = action != "Check"
        is_all_in = hero_bet >= remaining_bb - 1e-9

        if is_all_in:
            hero_tok = _all_in_token(pot, facing_bet, remaining_bb, is_opener)
        else:
            hero_tok = _hero_token(action, pot, facing_bet, remaining_bb)

        new_tokens = tokens_so_far + [hero_tok]
        sequences.append((cache_key, is_facing_aggression, is_all_in, new_tokens))

        new_remaining_bb = remaining_bb - hero_bet

        if action == "Check" and is_opener:
            villain_bet = min(VILLAIN_BET_FRACTION * pot, new_remaining_bb)
            if villain_bet > 0:
                villain_tok = _hero_token("B66", pot, 0.0, new_remaining_bb)
                deeper_tokens = new_tokens + [villain_tok]
                sub = _enumerate_sequences(
                    pot, villain_bet, new_remaining_bb,
                    _make_cache_key(cache_key, "B"),
                    is_opener=False,
                    tokens_so_far=deeper_tokens,
                )
                sequences.extend(sub)

        elif not is_all_in and new_remaining_bb > 0:
            villain_raise = min(VILLAIN_RAISE_MULTIPLIER * hero_bet, new_remaining_bb)
            if villain_raise > hero_bet:
                new_pot = pot + 2 * hero_bet
                new_facing = villain_raise - hero_bet
                villain_tok = _hero_token("R3x", new_pot, hero_bet, new_remaining_bb)
                deeper_tokens = new_tokens + [villain_tok]
                sub = _enumerate_sequences(
                    new_pot, new_facing, new_remaining_bb,
                    _make_cache_key(cache_key, "R"),
                    is_opener=False,
                    tokens_so_far=deeper_tokens,
                )
                sequences.extend(sub)

    return sequences


def _build_prediction_cache(
    model: SolverTransformer,
    board: list[Card],
    action_prefix: list[str],
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    starting_bb: float,
    hero_is_ip: bool,
) -> dict[str, tuple[float, float, float]]:
    """Phase 1: enumerate tree, batch predict, build cache."""
    is_opener = not hero_is_ip and facing_bet == 0.0
    sequences = _enumerate_sequences(
        pot, facing_bet, remaining_bb,
        cache_key_prefix="", is_opener=is_opener, tokens_so_far=[],
    )

    if not sequences:
        return {}

    base_tokens = _build_sequence_tokens(board, action_prefix)
    token_lists = [base_tokens + tokens for _, _, _, tokens in sequences]
    raw_probs = _batch_predict(model, token_lists, starting_bb)

    cache: dict[str, tuple[float, float, float]] = {}
    for i, (cache_key, is_facing_aggression, is_all_in, _) in enumerate(sequences):
        cache[cache_key] = _villain_response(raw_probs[i], is_facing_aggression, is_all_in)

    return cache

def _build_ranking_cache(
    board: list[Card],
    all_combos: list[tuple[Card, Card]],
) -> dict[tuple[Card, Card], int]:
    """Evaluate hand strength for all combos on this board. River only.
    Returns {normalized_combo: ranking_int} where higher = stronger hand."""
    e7_board = [_card_to_eval7(c) for c in board]
    rankings: dict[tuple[Card, Card], int] = {}
    for combo in all_combos:
        if _cards_conflict_with_board(combo, board):
            continue
        norm = _normalize_combo(combo)
        if norm in rankings:
            continue
        e7_hand = e7_board + [_card_to_eval7(combo[0]), _card_to_eval7(combo[1])]
        rankings[norm] = eval7.evaluate(e7_hand)
    return rankings


SUIT_INT = {'H': 0, 'D': 1, 'S': 2, 'C': 3}
RANK_INT = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6,
            '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}


def _card_int(c: Card) -> int:
    return RANK_INT[c.rank.value] * 4 + SUIT_INT[c.suit.value]


class EquityEngine:
    """Vectorized equity calculator using numpy broadcasting.

    Built once per solve_river call. Pre-computes overlap matrix and hero rankings.
    Each compute_equity call only needs to build villain arrays for the given sub-range.
    """

    def __init__(
        self,
        hero_combos: list[tuple[Card, Card]],
        ranking_cache: dict[tuple[Card, Card], int],
    ):
        self.hero_combos = hero_combos
        self.n_hero = len(hero_combos)
        self.hero_rankings = np.array(
            [ranking_cache.get(_normalize_combo(c), 0) for c in hero_combos],
            dtype=np.int64,
        )
        self.hero_c1 = np.array([_card_int(c[0]) for c in hero_combos], dtype=np.int32)
        self.hero_c2 = np.array([_card_int(c[1]) for c in hero_combos], dtype=np.int32)
        self._ranking_cache = ranking_cache

    def compute_equity(
        self, villain_range: dict[tuple[Card, Card], float],
    ) -> dict[tuple[Card, Card], float]:
        villain_combos = [c for c, f in villain_range.items() if f > 0]
        if not villain_combos:
            return {c: 0.5 for c in self.hero_combos}

        vil_rankings = np.array(
            [self._ranking_cache.get(_normalize_combo(c), 0) for c in villain_combos],
            dtype=np.int64,
        )
        vil_freqs = np.array([villain_range[c] for c in villain_combos], dtype=np.float64)
        vil_c1 = np.array([_card_int(c[0]) for c in villain_combos], dtype=np.int32)
        vil_c2 = np.array([_card_int(c[1]) for c in villain_combos], dtype=np.int32)

        overlap = (
            (self.hero_c1[:, None] == vil_c1[None, :]) |
            (self.hero_c1[:, None] == vil_c2[None, :]) |
            (self.hero_c2[:, None] == vil_c1[None, :]) |
            (self.hero_c2[:, None] == vil_c2[None, :])
        )

        wins = (self.hero_rankings[:, None] > vil_rankings[None, :]).astype(np.float64)
        ties = (self.hero_rankings[:, None] == vil_rankings[None, :]).astype(np.float64) * 0.5

        weighted = (wins + ties) * vil_freqs[None, :]
        weighted[overlap] = 0.0

        freq_broad = np.broadcast_to(vil_freqs[None, :], (self.n_hero, len(villain_combos))).copy()
        freq_broad[overlap] = 0.0

        total_weight = freq_broad.sum(axis=1)
        equity = np.where(total_weight > 0, weighted.sum(axis=1) / total_weight, 0.5)

        return {self.hero_combos[i]: float(equity[i]) for i in range(self.n_hero)}


def _narrow_range(
    villain_range: dict[tuple[Card, Card], float],
    board: list[Card],
    street: str,
    aggressive_pct: float,
    passive_pct: float,
) -> tuple[dict, dict]:
    """Split villain range into passive and aggressive sub-ranges by equity.
    Returns (passive_range, aggressive_range)."""
    if aggressive_pct <= 0:
        return villain_range, {}
    if passive_pct <= 0:
        return {}, villain_range

    _, passive_range, aggressive_range = filter_range_by_equity(
        villain_range, board, street,
        raise_pct=aggressive_pct * 100,
        call_pct=passive_pct * 100,
        hard_split=False,
    )
    return passive_range, aggressive_range


def _eval_action(
    action: str,
    board: list[Card],
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    action_seq: str,
    prediction_cache: dict[str, tuple[float, float, float]],
    equity_engine: EquityEngine,
    hero_combos: list[tuple[Card, Card]],
    is_opener: bool,
    street: str = "river",
) -> dict[tuple[Card, Card], float]:
    """Evaluate one hero action. Returns {combo: ev}."""

    if action == "Fold":
        return {combo: 0.0 for combo in hero_combos}

    if action == "Call" or (action == "Check" and not is_opener):
        equity = equity_engine.compute_equity(villain_range)
        return {
            combo: equity[combo] * (pot + facing_bet)
                   - (1 - equity[combo]) * facing_bet
            for combo in hero_combos
        }

    if action == "Check" and is_opener:
        cache_key = _make_cache_key(action_seq, "X")
        _, passive_pct, aggressive_pct = prediction_cache[cache_key]

        passive_range, aggressive_range = _narrow_range(
            villain_range, board, street, aggressive_pct, passive_pct,
        )

        eq_vs_passive = equity_engine.compute_equity(passive_range)
        ev_vs_passive = {combo: eq_vs_passive[combo] * pot for combo in hero_combos}

        villain_bet_bb = min(VILLAIN_BET_FRACTION * pot, remaining_bb)
        ev_vs_aggressive = _solve_node(
            board, pot, villain_bet_bb, remaining_bb, aggressive_range,
            _make_cache_key(cache_key, "B"),
            prediction_cache, equity_engine, hero_combos,
            is_opener=False, street=street,
        )

        return {
            combo: passive_pct * ev_vs_passive[combo]
                   + aggressive_pct * ev_vs_aggressive[combo]
            for combo in hero_combos
        }

    hero_bet = _compute_bet_size(action, pot, facing_bet, remaining_bb)
    token_str = _action_to_cache_token(action)
    cache_key = _make_cache_key(action_seq, token_str)
    fold_pct, passive_pct, aggressive_pct = prediction_cache[cache_key]
    is_all_in = hero_bet >= remaining_bb

    passive_range, aggressive_range = _narrow_range(
        villain_range, board, street, aggressive_pct, passive_pct,
    )

    fold_evs = {combo: pot + facing_bet for combo in hero_combos}

    eq_vs_passive = equity_engine.compute_equity(passive_range)
    call_evs = {
        combo: eq_vs_passive[combo] * (pot + hero_bet)
               - (1 - eq_vs_passive[combo]) * hero_bet
        for combo in hero_combos
    }

    if is_all_in or aggressive_pct <= 0:
        return {
            combo: fold_pct * fold_evs[combo]
                   + passive_pct * call_evs[combo]
            for combo in hero_combos
        }

    new_remaining_bb = remaining_bb - hero_bet
    villain_raise = min(VILLAIN_RAISE_MULTIPLIER * hero_bet, new_remaining_bb)

    if villain_raise <= hero_bet:
        # Villain can't meaningfully raise — redirect aggressive to call
        return {
            combo: fold_pct * fold_evs[combo]
                   + (passive_pct + aggressive_pct) * call_evs[combo]
            for combo in hero_combos
        }
    new_pot = pot + 2 * hero_bet
    new_facing = villain_raise - hero_bet

    raise_node_evs = _solve_node(
        board, new_pot, new_facing, new_remaining_bb, aggressive_range,
        _make_cache_key(cache_key, "R"),
        prediction_cache, equity_engine, hero_combos,
        is_opener=False, street=street,
    )

    return {
        combo: fold_pct * fold_evs[combo]
               + passive_pct * call_evs[combo]
               + aggressive_pct * (raise_node_evs[combo] - hero_bet)
        for combo in hero_combos
    }


def _solve_node(
    board: list[Card],
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    action_seq: str,
    prediction_cache: dict[str, tuple[float, float, float]],
    equity_engine: EquityEngine,
    hero_combos: list[tuple[Card, Card]],
    is_opener: bool,
    street: str = "river",
) -> dict[tuple[Card, Card], float]:
    """Inner recursion. Hero picks best action per combo."""
    hero_actions = _get_hero_actions(pot, facing_bet, remaining_bb, is_opener)

    action_evs: dict[str, dict[tuple[Card, Card], float]] = {}
    for action in hero_actions:
        action_evs[action] = _eval_action(
            action, board, pot, facing_bet, remaining_bb,
            villain_range, action_seq, prediction_cache, equity_engine,
            hero_combos, is_opener, street,
        )

    return {
        combo: max(action_evs[a][combo] for a in action_evs)
        for combo in hero_combos
    }


def solve_river(
    board: list[Card],
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    model: SolverTransformer,
    action_prefix: list[str],
    hero_combos: list[tuple[Card, Card]],
    starting_bb: float,
    hero_is_ip: bool,
) -> tuple[dict[str, dict[tuple[Card, Card], float]], dict[tuple[Card, Card], float]]:
    """Solve river spot.

    Returns (action_evs, combo_equity) where:
      action_evs = {action: {combo: ev}} — does NOT pick max (UI shows all actions)
      combo_equity = {combo: equity} — frequency-weighted equity vs villain range
    """
    prediction_cache = _build_prediction_cache(
        model, board, action_prefix, pot, facing_bet, remaining_bb, starting_bb,
        hero_is_ip,
    )
    all_combos = hero_combos + list(villain_range.keys())
    ranking_cache = _build_ranking_cache(board, all_combos)
    equity_engine = EquityEngine(hero_combos, ranking_cache)
    is_opener = not hero_is_ip and facing_bet == 0.0

    hero_actions = _get_hero_actions(pot, facing_bet, remaining_bb, is_opener)
    results: dict[str, dict[tuple[Card, Card], float]] = {}
    all_in_computed = False

    for action in hero_actions:
        bet_size = _compute_bet_size(action, pot, facing_bet, remaining_bb)
        is_all_in = action not in ("Check", "Fold", "Call") and bet_size >= remaining_bb - 1e-9

        if is_all_in:
            if all_in_computed:
                continue
            all_in_computed = True
            display_key = "All-in"
        else:
            display_key = action

        results[display_key] = _eval_action(
            action, board, pot, facing_bet, remaining_bb,
            villain_range, "", prediction_cache, equity_engine,
            hero_combos, is_opener, "river",
        )

    combo_equity = {
        _normalize_combo(combo): eq
        for combo, eq in equity_engine.compute_equity(villain_range).items()
    }
    return results, combo_equity

def full_solve_spot(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    pot_bb: float,
    starting_bb: float,
    valid_combos: list[tuple[Card, Card]],
    hero_is_ip: bool,
    facing_bet: float = 0.0,
) -> tuple[dict[str, dict[tuple[Card, Card], float]], dict[tuple[Card, Card], float] | None]:
    """Drop-in replacement for mc_solve_spot.
    Returns (action_evs, combo_equity). combo_equity is None for non-river streets."""
    if street != "river":
        return mc_solve_spot(
            model, board, street, action_prefix, hero_actions,
            villain_range, pot_bb, starting_bb, valid_combos, hero_is_ip,
        ), None

    is_opener = not hero_is_ip and "Check" in hero_actions

    if facing_bet <= 0 and not is_opener:
        last_prefix_action = action_prefix[-1].split(":")[-1] if action_prefix else ""
        if last_prefix_action == "All-in":
            facing_bet = 2 * starting_bb - pot_bb
        else:
            facing_bet = _compute_facing_bet(action_prefix, pot_bb)

    matched_pot = pot_bb - facing_bet
    remaining_bb = starting_bb - matched_pot / 2

    return solve_river(
        board=board,
        pot=matched_pot,
        facing_bet=facing_bet,
        remaining_bb=remaining_bb,
        villain_range=villain_range,
        model=model,
        action_prefix=action_prefix,
        hero_combos=valid_combos,
        starting_bb=starting_bb,
        hero_is_ip=hero_is_ip,
    )


def full_solve_spot_streaming(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    pot_bb: float,
    starting_bb: float,
    valid_combos: list[tuple[Card, Card]],
    hero_is_ip: bool,
    facing_bet: float = 0.0,
) -> Generator:
    """Drop-in replacement for mc_solve_spot_streaming."""
    if street != "river":
        yield from mc_solve_spot_streaming(
            model, board, street, action_prefix, hero_actions,
            villain_range, pot_bb, starting_bb, valid_combos, hero_is_ip,
        )
        return

    result, combo_equity = full_solve_spot(
        model, board, street, action_prefix, hero_actions,
        villain_range, pot_bb, starting_bb, valid_combos, hero_is_ip,
        facing_bet=facing_bet,
    )

    update: dict = {
        "type": "complete",
        "progress": 1.0,
        "simsComplete": 1,
        "totalCards": 1,
        "combo_evs": _serialize(result, valid_combos),
        "action_keys": list(result.keys()),
    }
    if combo_equity is not None:
        equity_serialized: dict[str, float] = {}
        for combo, eq in combo_equity.items():
            cs = f"{combo[0].rank.value}{combo[0].suit.value}{combo[1].rank.value}{combo[1].suit.value}"
            equity_serialized[cs] = round(eq, 4)
        update["combo_equity"] = equity_serialized
    yield update
