"""Recursive turn solver — extends the river solver to handle turn spots.

Terminal states on the turn resolve by dealing a river card and calling
solve_river() for each possible card, then averaging the results.

Same two-phase architecture as the river solver:
  1. Enumerate turn game tree → batch predict all villain response nodes → fill prediction cache.
  2. Recurse through tree computing EV, with turn terminals delegating to solve_river.
"""
from __future__ import annotations

import logging
from typing import Callable, Generator

from playing_cards_lib.core import Card, Rank, Suit

from solver.model.transformer import SolverTransformer
from solver.eq_calculator import _cards_conflict_with_board
from solver.streets.common import (
    VILLAIN_BET_FRACTION,
    VILLAIN_RAISE_MULTIPLIER,
    HERO_BET_FRACTIONS,
    _compute_bet_size,
    _get_hero_actions,
    _action_to_cache_token,
    _make_cache_key,
    _build_prediction_cache,
    _build_ranking_cache,
    _enumerate_sequences,
    _villain_response,
    EquityEngine,
    _narrow_range,
)
from solver.streets.mc_solver import _batch_predict
from solver.ev_calculator import _build_sequence_tokens
from solver.streets.river import solve_river

logger = logging.getLogger(__name__)

ALL_CARDS = [Card(r, s) for r in Rank for s in Suit]


def _remaining_deck(board: list[Card]) -> list[Card]:
    board_set = set(board)
    return [c for c in ALL_CARDS if c not in board_set]


def _solve_river_for_all_cards(
    board: list[Card],
    pot: float,
    remaining_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    model: SolverTransformer,
    action_prefix: list[str],
    hero_combos: list[tuple[Card, Card]],
    starting_bb: float,
    hero_is_ip: bool,
    on_river_solve: Callable[[], None] | None = None,
) -> dict[tuple[Card, Card], float]:
    """Enumerate all river cards, solve each, average per-combo best EVs.

    Mega-batches all river cards' prediction caches into one model call,
    then solves each card analytically (no further model calls needed).

    When remaining_bb <= 0 (all-in on turn), computes showdown equity directly.

    on_river_solve is called after each river card is processed (for progress tracking).
    """
    deck = _remaining_deck(board)

    combo_ev_sum: dict[tuple[Card, Card], float] = {c: 0.0 for c in hero_combos}
    combo_count: dict[tuple[Card, Card], int] = {c: 0 for c in hero_combos}

    if remaining_bb <= 1e-9:
        return _equity_only_river_enum(
            board, deck, pot, villain_range, hero_combos, on_river_solve,
        )

    is_opener = not hero_is_ip
    sequences = _enumerate_sequences(
        pot, 0.0, remaining_bb,
        cache_key_prefix="", is_opener=is_opener, tokens_so_far=[],
    )

    if not sequences:
        return {c: 0.0 for c in hero_combos}

    mega_token_lists = []
    card_indices: list[int] = []

    for card_idx, river_card in enumerate(deck):
        board_5 = board + [river_card]
        river_prefix = action_prefix + [
            f"{river_card.rank.value}{river_card.suit.value}"
        ]
        base_tokens = _build_sequence_tokens(board_5, river_prefix)
        for _, _, _, tokens in sequences:
            mega_token_lists.append(base_tokens + tokens)
            card_indices.append(card_idx)

    mega_probs = _batch_predict(model, mega_token_lists, starting_bb)

    num_sequences = len(sequences)
    card_caches: list[dict[str, tuple[float, float, float]]] = [
        {} for _ in range(len(deck))
    ]
    for batch_idx in range(len(mega_token_lists)):
        cidx = card_indices[batch_idx]
        seq_idx = batch_idx % num_sequences
        cache_key, is_facing, is_all_in_seq, _ = sequences[seq_idx]
        card_caches[cidx][cache_key] = _villain_response(
            mega_probs[batch_idx], is_facing, is_all_in_seq,
        )

    for card_idx, river_card in enumerate(deck):
        board_5 = board + [river_card]
        valid_combos = [
            c for c in hero_combos
            if river_card != c[0] and river_card != c[1]
        ]
        valid_villain = {
            c: f for c, f in villain_range.items()
            if river_card != c[0] and river_card != c[1]
        }
        if not valid_combos or not valid_villain:
            if on_river_solve:
                on_river_solve()
            continue

        action_evs, _ = solve_river(
            board=board_5,
            pot=pot,
            facing_bet=0.0,
            remaining_bb=remaining_bb,
            villain_range=valid_villain,
            model=model,
            action_prefix=action_prefix,
            hero_combos=valid_combos,
            starting_bb=starting_bb,
            hero_is_ip=hero_is_ip,
            prediction_cache=card_caches[card_idx],
        )

        for combo in valid_combos:
            best_ev = max(
                action_evs[a].get(combo, 0.0)
                for a in action_evs
            )
            combo_ev_sum[combo] += best_ev
            combo_count[combo] += 1

        if on_river_solve:
            on_river_solve()

    return {
        combo: combo_ev_sum[combo] / combo_count[combo]
        if combo_count[combo] > 0 else 0.0
        for combo in hero_combos
    }


def _equity_only_river_enum(
    board: list[Card],
    deck: list[Card],
    pot: float,
    villain_range: dict[tuple[Card, Card], float],
    hero_combos: list[tuple[Card, Card]],
    on_river_solve: Callable[[], None] | None = None,
) -> dict[tuple[Card, Card], float]:
    """All-in path: enumerate river cards and compute equity directly."""
    combo_ev_sum: dict[tuple[Card, Card], float] = {c: 0.0 for c in hero_combos}
    combo_count: dict[tuple[Card, Card], int] = {c: 0 for c in hero_combos}

    for river_card in deck:
        board_5 = board + [river_card]
        valid_combos = [
            c for c in hero_combos
            if river_card != c[0] and river_card != c[1]
        ]
        valid_villain = {
            c: f for c, f in villain_range.items()
            if river_card != c[0] and river_card != c[1]
        }
        if not valid_combos or not valid_villain:
            if on_river_solve:
                on_river_solve()
            continue

        all_combos = list(valid_combos) + list(valid_villain.keys())
        ranking_cache = _build_ranking_cache(board_5, all_combos)
        engine = EquityEngine(valid_combos, ranking_cache)
        equity = engine.compute_equity(valid_villain)
        for combo in valid_combos:
            combo_ev_sum[combo] += equity[combo] * pot
            combo_count[combo] += 1
        if on_river_solve:
            on_river_solve()

    return {
        combo: combo_ev_sum[combo] / combo_count[combo]
        if combo_count[combo] > 0 else 0.0
        for combo in hero_combos
    }


def _eval_action_turn(
    action: str,
    board: list[Card],
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    action_seq: str,
    prediction_cache: dict[str, tuple[float, float, float]],
    model: SolverTransformer,
    action_prefix: list[str],
    hero_combos: list[tuple[Card, Card]],
    starting_bb: float,
    hero_is_ip: bool,
    is_opener: bool,
    on_river_solve: Callable[[], None] | None = None,
) -> dict[tuple[Card, Card], float]:
    """Evaluate one hero action on the turn. Returns {combo: ev}."""

    if action == "Fold":
        return {combo: 0.0 for combo in hero_combos}

    if action == "Call" or (action == "Check" and not is_opener):
        new_pot = pot + 2 * facing_bet if action == "Call" else pot
        cost = facing_bet if action == "Call" else 0.0
        new_remaining = remaining_bb - cost

        river_avg = _solve_river_for_all_cards(
            board, new_pot, new_remaining, villain_range, model,
            action_prefix, hero_combos, starting_bb, hero_is_ip,
            on_river_solve,
        )
        return {combo: river_avg[combo] - cost for combo in hero_combos}

    if action == "Check" and is_opener:
        cache_key = _make_cache_key(action_seq, "X")
        _, passive_pct, aggressive_pct = prediction_cache[cache_key]

        passive_range, aggressive_range = _narrow_range(
            villain_range, board, "turn", aggressive_pct, passive_pct,
        )

        river_avg_passive = _solve_river_for_all_cards(
            board, pot, remaining_bb, passive_range, model,
            action_prefix, hero_combos, starting_bb, hero_is_ip,
            on_river_solve,
        )
        ev_vs_passive = {combo: river_avg_passive[combo] for combo in hero_combos}

        villain_bet_bb = min(VILLAIN_BET_FRACTION * pot, remaining_bb)
        ev_vs_aggressive = _solve_node_turn(
            board, pot, villain_bet_bb, remaining_bb, aggressive_range,
            _make_cache_key(cache_key, "B"),
            prediction_cache, model, action_prefix, hero_combos,
            starting_bb, hero_is_ip, is_opener=False,
            on_river_solve=on_river_solve,
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
    is_all_in = hero_bet >= remaining_bb - 1e-9

    passive_range, aggressive_range = _narrow_range(
        villain_range, board, "turn", aggressive_pct, passive_pct,
    )

    fold_evs = {combo: pot + facing_bet for combo in hero_combos}

    new_pot = pot + 2 * hero_bet
    new_remaining = remaining_bb - hero_bet

    river_avg_passive = _solve_river_for_all_cards(
        board, new_pot, new_remaining, passive_range, model,
        action_prefix, hero_combos, starting_bb, hero_is_ip,
        on_river_solve,
    )
    call_evs = {combo: river_avg_passive[combo] - hero_bet for combo in hero_combos}

    if is_all_in or aggressive_pct <= 0:
        return {
            combo: fold_pct * fold_evs[combo]
                   + passive_pct * call_evs[combo]
            for combo in hero_combos
        }

    villain_raise = min(VILLAIN_RAISE_MULTIPLIER * hero_bet, new_remaining)
    if villain_raise <= hero_bet:
        return {
            combo: fold_pct * fold_evs[combo]
                   + (passive_pct + aggressive_pct) * call_evs[combo]
            for combo in hero_combos
        }

    raise_pot = pot + 2 * hero_bet
    raise_facing = villain_raise - hero_bet

    raise_node_evs = _solve_node_turn(
        board, raise_pot, raise_facing, new_remaining, aggressive_range,
        _make_cache_key(cache_key, "R"),
        prediction_cache, model, action_prefix, hero_combos,
        starting_bb, hero_is_ip, is_opener=False,
        on_river_solve=on_river_solve,
    )

    return {
        combo: fold_pct * fold_evs[combo]
               + passive_pct * call_evs[combo]
               + aggressive_pct * (raise_node_evs[combo] - hero_bet)
        for combo in hero_combos
    }


def _solve_node_turn(
    board: list[Card],
    pot: float,
    facing_bet: float,
    remaining_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    action_seq: str,
    prediction_cache: dict[str, tuple[float, float, float]],
    model: SolverTransformer,
    action_prefix: list[str],
    hero_combos: list[tuple[Card, Card]],
    starting_bb: float,
    hero_is_ip: bool,
    is_opener: bool,
    on_river_solve: Callable[[], None] | None = None,
) -> dict[tuple[Card, Card], float]:
    """Inner recursion on turn. Hero picks best action per combo."""
    hero_actions = _get_hero_actions(pot, facing_bet, remaining_bb, is_opener)

    action_evs: dict[str, dict[tuple[Card, Card], float]] = {}
    for action in hero_actions:
        action_evs[action] = _eval_action_turn(
            action, board, pot, facing_bet, remaining_bb,
            villain_range, action_seq, prediction_cache,
            model, action_prefix, hero_combos,
            starting_bb, hero_is_ip, is_opener,
            on_river_solve,
        )

    return {
        combo: max(action_evs[a][combo] for a in action_evs)
        for combo in hero_combos
    }


def solve_turn(
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
    on_river_solve: Callable[[], None] | None = None,
) -> tuple[dict[str, dict[tuple[Card, Card], float]], None]:
    """Solve turn spot.

    Returns (action_evs, None) where:
      action_evs = {action: {combo: ev}} — all hero actions (UI shows all).
      combo_equity is None (no single equity value on the turn).
    """
    prediction_cache = _build_prediction_cache(
        model, board, action_prefix, pot, facing_bet, remaining_bb,
        starting_bb, hero_is_ip,
    )
    is_opener = not hero_is_ip and facing_bet == 0.0

    hero_actions = _get_hero_actions(pot, facing_bet, remaining_bb, is_opener)
    results: dict[str, dict[tuple[Card, Card], float]] = {}
    all_in_computed = False

    for action in hero_actions:
        bet_size = _compute_bet_size(action, pot, facing_bet, remaining_bb)
        is_all_in = (
            action not in ("Check", "Fold", "Call")
            and bet_size >= remaining_bb - 1e-9
        )

        if is_all_in:
            if all_in_computed:
                continue
            all_in_computed = True
            display_key = "All-in"
        else:
            display_key = action

        results[display_key] = _eval_action_turn(
            action, board, pot, facing_bet, remaining_bb,
            villain_range, "", prediction_cache,
            model, action_prefix, hero_combos,
            starting_bb, hero_is_ip, is_opener,
            on_river_solve,
        )

    return results, None
