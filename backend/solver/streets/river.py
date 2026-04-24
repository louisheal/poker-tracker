"""Recursive river solver — full tree enumeration with batch model inference.

Two phases:
  1. Enumerate game tree → batch predict all villain response nodes → fill prediction cache.
  2. Recurse through tree computing EV with O(1) cache lookups + hand ranking comparisons.
"""
from __future__ import annotations

import logging
from typing import Generator

from playing_cards_lib.core import Card

from solver.model.transformer import SolverTransformer
from solver.eq_calculator import _normalize_combo
from solver.streets.mc_solver import (
    _compute_facing_bet,
    _serialize,
    mc_solve_spot,
    mc_solve_spot_streaming,
)
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
    EquityEngine,
    _narrow_range,
)

logger = logging.getLogger(__name__)


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
    if street != "river" and street != "turn":
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

    if street == "turn":
        from solver.streets.turn import solve_turn
        return solve_turn(
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
    if street != "river" and street != "turn":
        yield from mc_solve_spot_streaming(
            model, board, street, action_prefix, hero_actions,
            villain_range, pot_bb, starting_bb, valid_combos, hero_is_ip,
        )
        return

    if street == "turn":
        yield from _turn_streaming(
            model, board, action_prefix, hero_actions, villain_range,
            pot_bb, starting_bb, valid_combos, hero_is_ip, facing_bet,
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


def _turn_streaming(
    model: SolverTransformer,
    board: list[Card],
    action_prefix: list[str],
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    pot_bb: float,
    starting_bb: float,
    valid_combos: list[tuple[Card, Card]],
    hero_is_ip: bool,
    facing_bet: float,
) -> Generator:
    """Stream turn solver progress. Yields updates as river cards are solved."""
    import queue as queue_mod
    import threading

    from solver.streets.turn import solve_turn, _remaining_deck
    from solver.streets.common import _enumerate_sequences, _get_hero_actions

    is_opener = not hero_is_ip and facing_bet == 0.0
    if facing_bet <= 0 and not is_opener:
        last_prefix_action = action_prefix[-1].split(":")[-1] if action_prefix else ""
        if last_prefix_action == "All-in":
            facing_bet = 2 * starting_bb - pot_bb
        else:
            facing_bet = _compute_facing_bet(action_prefix, pot_bb)
    matched_pot = pot_bb - facing_bet
    remaining_bb = starting_bb - matched_pot / 2

    deck_size = len(_remaining_deck(board))
    sequences = _enumerate_sequences(
        matched_pot, facing_bet, remaining_bb,
        cache_key_prefix="", is_opener=is_opener, tokens_so_far=[],
    )
    river_call_count = sum(1 for _, _, _, _ in sequences)
    total_river_solves = max(river_call_count * deck_size, 1)

    progress_queue: queue_mod.Queue = queue_mod.Queue()
    progress_count = [0]

    def on_river_solve():
        progress_count[0] += 1
        progress_queue.put(progress_count[0])

    result_holder: list = [None]
    error_holder: list = [None]

    def _run():
        try:
            result_holder[0] = solve_turn(
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
                on_river_solve=on_river_solve,
            )
        except Exception as e:
            error_holder[0] = e
        finally:
            progress_queue.put(None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    yield {"type": "progress", "stage": "solving", "totalCards": total_river_solves}

    last_yielded = 0
    while True:
        try:
            item = progress_queue.get(timeout=0.5)
        except queue_mod.Empty:
            continue

        if item is None:
            break

        current = item
        if current - last_yielded >= max(total_river_solves // 20, 1):
            progress = min(current / total_river_solves, 0.99)
            yield {
                "type": "progress",
                "progress": round(progress, 3),
                "simsComplete": current,
                "totalCards": total_river_solves,
            }
            last_yielded = current

    thread.join()

    if error_holder[0]:
        raise error_holder[0]

    result, _ = result_holder[0]

    yield {
        "type": "complete",
        "progress": 1.0,
        "simsComplete": progress_count[0],
        "totalCards": total_river_solves,
        "combo_evs": _serialize(result, valid_combos),
        "action_keys": list(result.keys()),
    }
