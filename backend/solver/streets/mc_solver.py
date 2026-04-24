"""Monte Carlo tree solver for EV computation.

Batched, level-by-level solver that enumerates all turn/river cards.
Model predictions are mega-batched across all cards before computing EVs.

Architecture (from flop):
  1. Batch-predict villain responses for each turn card × hero action
  2. For each turn card: compute hero EV using predictions + equity
  3. Average across all turn cards for continuation value
  4. Combine with current-street villain response for final EV

One raise per street (bet → raise OK, raise → reraise not).
"""

from __future__ import annotations

import logging
import random
import time

import numpy as np
import torch

from playing_cards_lib.core import Card, Rank, Suit

from solver.model.transformer import SolverTransformer
from solver.eq_calculator import all_hands_vs_range
from solver.ev_calculator import (
    _build_sequence_tokens,
    _action_key_to_model_action,
    ACTION_TO_BET_PCT,
    RAISE_MULTIPLIER,
    MAX_SEQ_LEN,
)
from solver.ranges import filter_range_by_equity, _normalize_combo, _cards_conflict
from solver.models import Token, TokenType

logger = logging.getLogger(__name__)

HERO_OPEN_ACTIONS = ["Check", "B33", "B66", "B133", "B200"]
NEXT_STREET = {"flop": "turn", "turn": "river"}
_ALL_CARDS = [Card(r, s) for r in Rank for s in Suit]

VILLAIN_BET_SIZE = 0.66  # villain bets 66% pot when hero checks

def _remaining_deck(board: list[Card]) -> list[Card]:
    board_set = {(c.rank, c.suit) for c in board}
    return [c for c in _ALL_CARDS if (c.rank, c.suit) not in board_set]


def _card_in_combo(card: Card, combo: tuple[Card, Card]) -> bool:
    return ((card.rank == combo[0].rank and card.suit == combo[0].suit) or
            (card.rank == combo[1].rank and card.suit == combo[1].suit))


def _remove_card_from_range(
    range_: dict[tuple[Card, Card], float], card: Card,
) -> dict[tuple[Card, Card], float]:
    return {c: f for c, f in range_.items() if not _card_in_combo(card, c)}


def _clip(amount: float, stack: float) -> float:
    return min(amount, max(stack, 0.0))


def _bet_bb(action: str, pot: float, facing: float) -> float:
    if action == "B33":
        return 0.33 * pot
    elif action == "B66":
        return 0.66 * pot
    elif action == "B133":
        return 1.33 * pot
    elif action == "B200":
        return 2.0 * pot
    elif action == "R3x":
        return 3.0 * facing
    return 0.0


def _hero_token(action: str, pot: float, facing: float, stack: float) -> Token:
    bet_pct = ACTION_TO_BET_PCT.get(action, 0.0)
    model_action = _action_key_to_model_action(action)
    if action in ("Check", "Fold"):
        bb = 0.0
    elif action == "Call":
        bb = 0.0
    elif action in RAISE_MULTIPLIER:
        bb = _clip(RAISE_MULTIPLIER[action] * facing, stack)
    else:
        bb = _clip(_bet_bb(action, pot, facing), stack)
    return Token(TokenType.ACTION, action=model_action,
                 bet_size_pct=bet_pct, bet_size_bb=bb)


def _villain_probs(probs: torch.Tensor, facing_bet: bool) -> tuple[float, float, float]:
    """Extract fold/call/raise from model output."""
    if facing_bet:
        fold_pct = probs[0].item()
        passive_pct = probs[1].item() + probs[2].item()
        aggressive_pct = probs[3].item() + probs[4].item()
    else:
        fold_pct = 0.0
        passive_pct = probs[1].item() + probs[2].item()
        aggressive_pct = probs[3].item() + probs[4].item()
    total = fold_pct + passive_pct + aggressive_pct
    if total > 0:
        return fold_pct / total, passive_pct / total, aggressive_pct / total
    return 0.0, 0.5, 0.5

def _tensorize_many(
    token_lists: list[list[Token]], starting_bb: float,
) -> dict[str, torch.Tensor]:
    batch_size = len(token_lists)
    tt = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.int64)
    rk = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.int64)
    su = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.int64)
    ac = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.int64)
    bs = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.float32)
    bb = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.float32)
    si = np.zeros((batch_size, MAX_SEQ_LEN), dtype=np.int64)
    pm = np.ones((batch_size, MAX_SEQ_LEN), dtype=np.bool_)

    for b, tokens in enumerate(token_lists):
        n = min(len(tokens), MAX_SEQ_LEN)
        for i in range(n):
            tok = tokens[i]
            tt[b, i] = int(tok.token_type)
            rk[b, i] = tok.rank
            su[b, i] = tok.suit
            ac[b, i] = tok.action
            bs[b, i] = tok.bet_size_pct
            bb[b, i] = tok.bet_size_bb
            si[b, i] = tok.action if tok.token_type == TokenType.STREET_MARKER else 0
        pm[b, :n] = False

    return {
        "token_types": torch.from_numpy(tt),
        "ranks": torch.from_numpy(rk),
        "suits": torch.from_numpy(su),
        "actions": torch.from_numpy(ac),
        "bet_sizes": torch.from_numpy(bs),
        "bet_sizes_bb": torch.from_numpy(bb),
        "street_ids": torch.from_numpy(si),
        "padding_mask": torch.from_numpy(pm),
        "stack_sizes": torch.full((batch_size,), starting_bb / 100.0, dtype=torch.float),
    }


def _batch_predict(
    model: SolverTransformer,
    token_lists: list[list[Token]],
    stack_bb: float,
    batch_size: int = 1024,
) -> torch.Tensor:
    """Run model on N sequences, return (N, 5) softmax probs."""
    if not token_lists:
        return torch.empty(0, 5)
    device = next(model.parameters()).device
    chunks = []
    with torch.no_grad():
        for i in range(0, len(token_lists), batch_size):
            batch = _tensorize_many(token_lists[i:i + batch_size], stack_bb)
            batch = {k: v.to(device, non_blocking=True) for k, v in batch.items()}
            logits = model(batch)
            chunks.append(torch.softmax(logits, dim=-1).cpu())
    return torch.cat(chunks, dim=0)

def _showdown_ev(
    board: list[Card],
    pot_bb: float,
    villain_range: dict[tuple[Card, Card], float],
    valid_combos: list[tuple[Card, Card]],
    equity_cache: dict[tuple, dict],
) -> dict[tuple[Card, Card], float]:
    """equity × pot for a 5-card board."""
    board_key = tuple(sorted((c.rank.value, c.suit.value) for c in board))
    # Include villain range identity in cache key (different sub-ranges need separate equity)
    range_id = id(villain_range)
    cache_key = (board_key, range_id)
    if cache_key not in equity_cache:
        equity_cache[cache_key] = all_hands_vs_range(
            valid_combos, villain_range, board,
        )
    eq = equity_cache[cache_key]
    return {c: eq.get(_normalize_combo(c), 0.5) * pot_bb for c in valid_combos}

def _solve_river(
    board: list[Card],
    pot_bb: float,
    stack: float,
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    model: SolverTransformer,
    action_prefix: list[str],
    stack_bb: float,
    valid_combos: list[tuple[Card, Card]],
    equity_cache: dict[tuple, dict],
    facing_bet: float = 0.0,
) -> dict[str, dict[tuple[Card, Card], float]]:
    """Solve a river spot: hero acts, villain responds, showdown."""
    base = _build_sequence_tokens(board, action_prefix)
    seqs: list[list[Token]] = []
    keys: list[str] = []

    for a in hero_actions:
        if a == "Fold":
            continue
        seqs.append(base + [_hero_token(a, pot_bb, facing_bet, stack)])
        keys.append(a)

    all_probs = _batch_predict(model, seqs, stack_bb)
    results: dict[str, dict[tuple[Card, Card], float]] = {}

    for idx, action in enumerate(keys):
        probs = all_probs[idx]
        is_agg = action not in ("Check", "Call")
        fp, cp, rp = _villain_probs(probs, is_agg)

        # Range narrowing
        if villain_range and board:
            raise_r, call_r, _ = filter_range_by_equity(
                villain_range, board, "river",
                raise_pct=rp * 100, call_pct=cp * 100, hard_split=True,
            )
        else:
            raise_r = call_r = villain_range

        if action == "Check":
            # check back → showdown
            check_ev = _showdown_ev(board, pot_bb, call_r, valid_combos, equity_cache)
            # villain bets → hero fold(0) or call
            vb = _clip(VILLAIN_BET_SIZE * pot_bb, stack)
            if vb > 0:
                call_cost = vb
                sd = _showdown_ev(
                    board, pot_bb + vb + call_cost, raise_r,
                    valid_combos, equity_cache,
                )
                bet_ev = {c: max(0.0, sd[c] - call_cost) for c in valid_combos}
            else:
                bet_ev = {c: 0.0 for c in valid_combos}

            results[action] = {
                c: cp * check_ev[c] + rp * bet_ev[c] for c in valid_combos
            }

        elif action == "Call":
            cost = facing_bet
            sd = _showdown_ev(
                board, pot_bb + cost, villain_range, valid_combos, equity_cache,
            )
            results[action] = {c: sd[c] - cost for c in valid_combos}

        else:
            # bet/raise
            bet = _clip(_bet_bb(action, pot_bb, facing_bet), stack)
            if bet <= 0:
                results[action] = {c: 0.0 for c in valid_combos}
                continue

            # fold: hero wins pot + gets bet back
            fold_ev = pot_bb + bet
            # call: showdown
            sd_call = _showdown_ev(
                board, pot_bb + bet + bet, call_r, valid_combos, equity_cache,
            )
            # raise: villain raises 3×, hero fold(0) or call
            vr = _clip(3.0 * bet, stack - bet)
            if vr > 0 and rp > 0.001:
                hc = vr - bet  # hero's additional call cost
                sd_raise = _showdown_ev(
                    board, pot_bb + 2 * vr, raise_r,
                    valid_combos, equity_cache,
                )
                raise_ev = {c: max(0.0, sd_raise[c] - hc) for c in valid_combos}
            else:
                raise_ev = {c: 0.0 for c in valid_combos}

            results[action] = {
                c: fp * fold_ev + cp * sd_call[c] + rp * raise_ev[c] - bet
                for c in valid_combos
            }

    if "Fold" in hero_actions:
        results["Fold"] = {c: 0.0 for c in valid_combos}

    return results

def _solve_turn_card(
    board_5: list[Card],
    pot_bb: float,
    stack: float,
    villain_range: dict[tuple[Card, Card], float],
    model: SolverTransformer,
    action_prefix: list[str],
    stack_bb: float,
    valid_combos: list[tuple[Card, Card]],
    equity_cache: dict[tuple, dict],
    card_probs: dict[str, torch.Tensor],
    card: Card,
) -> dict[tuple[Card, Card], float]:
    """Solve a single turn→river card. Returns best hero EV per combo.

    card_probs has pre-computed villain predictions for each hero action.
    """
    best = {c: 0.0 for c in valid_combos}

    for action in HERO_OPEN_ACTIONS:
        if action == "Fold":
            continue
        probs = card_probs.get(action)
        if probs is None:
            continue

        is_agg = action not in ("Check", "Call")
        fp, cp, rp = _villain_probs(probs, is_agg)

        bet = _clip(_bet_bb(action, pot_bb, 0.0), stack)

        # Range narrowing for river board
        if villain_range and board_5:
            raise_r, call_r, _ = filter_range_by_equity(
                villain_range, board_5, "river",
                raise_pct=rp * 100, call_pct=cp * 100, hard_split=True,
            )
        else:
            raise_r = call_r = villain_range

        if action == "Check":
            check_ev = _showdown_ev(board_5, pot_bb, call_r, valid_combos, equity_cache)
            vb = _clip(VILLAIN_BET_SIZE * pot_bb, stack)
            if vb > 0:
                hc = vb
                sd = _showdown_ev(
                    board_5, pot_bb + vb + hc, raise_r,
                    valid_combos, equity_cache,
                )
                bet_ev = {c: max(0.0, sd[c] - hc) for c in valid_combos}
            else:
                bet_ev = {c: 0.0 for c in valid_combos}

            for c in valid_combos:
                if not _card_in_combo(card, c):
                    ev = cp * check_ev[c] + rp * bet_ev[c]
                    best[c] = max(best[c], ev)

        else:
            if bet <= 0:
                continue
            fold_ev = pot_bb + bet
            sd_call = _showdown_ev(
                board_5, pot_bb + bet + bet, call_r,
                valid_combos, equity_cache,
            )
            vr = _clip(3.0 * bet, stack - bet)
            if vr > 0 and rp > 0.001:
                hc = vr - bet  # hero's additional call cost
                sd_raise = _showdown_ev(
                    board_5, pot_bb + 2 * vr, raise_r,
                    valid_combos, equity_cache,
                )
                raise_ev = {c: max(0.0, sd_raise[c] - hc) for c in valid_combos}
            else:
                raise_ev = {c: 0.0 for c in valid_combos}

            for c in valid_combos:
                if not _card_in_combo(card, c):
                    ev = fp * fold_ev + cp * sd_call[c] + rp * raise_ev[c] - bet
                    best[c] = max(best[c], ev)

    return best

def _compute_facing_bet(action_prefix: list[str], pot_bb: float) -> float:
    if not action_prefix:
        return 0.0
    last = action_prefix[-1].split(":")[-1]
    pct = ACTION_TO_BET_PCT.get(last, 0.0)
    mult = RAISE_MULTIPLIER.get(last, 0.0)
    if mult > 0:
        return mult * (pot_bb * 0.5)
    elif pct > 0:
        pot_before = pot_bb / (1.0 + pct / 100.0)
        return pot_before * pct / 100.0
    return 0.0


def mc_solve_spot(
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
) -> dict[str, dict[tuple[Card, Card], float]]:
    """Solve a spot. Returns {action: {combo: ev}}."""
    equity_cache: dict[tuple, dict] = {}
    facing = _compute_facing_bet(action_prefix, pot_bb)

    if street == "river":
        return _solve_river(
            board, pot_bb, starting_bb, hero_actions,
            villain_range, model, action_prefix,
            starting_bb, valid_combos, equity_cache,
            facing_bet=facing,
        )

    # Non-river: enumerate next-street cards
    result = _solve_with_enumeration(
        model, board, street, action_prefix, hero_actions,
        villain_range, pot_bb, starting_bb,
        valid_combos, hero_is_ip, equity_cache, facing,
    )
    return result


def _combine_continuation(
    hero_actions: list[str],
    cur_villain: dict[str, tuple[float, float, float]],
    continuation: dict[tuple[Card, Card], float],
    valid_combos: list[tuple[Card, Card]],
    pot_bb: float,
    facing_bet: float,
    stack_bb: float,
) -> dict[str, dict[tuple[Card, Card], float]]:
    """Combine continuation EVs with current-street villain response.

    NOTE: continuation was computed at pot_bb with the full villain range.
    Ideally we'd recompute per-action with narrowed ranges and correct pots,
    but that's too expensive. The unscaled continuation is a reasonable
    approximation since relative action ordering is mostly equity-driven.
    """
    results: dict[str, dict[tuple[Card, Card], float]] = {}

    for a in hero_actions:
        if a == "Fold":
            results[a] = {c: 0.0 for c in valid_combos}
            continue

        fp, cp_pct, rp = cur_villain.get(a, (0.0, 0.5, 0.5))

        if a == "Call":
            results[a] = {c: continuation[c] - facing_bet for c in valid_combos}
        elif a == "Check":
            vb = _clip(VILLAIN_BET_SIZE * pot_bb, stack_bb)
            results[a] = {
                c: cp_pct * continuation[c]
                   + rp * max(0.0, continuation[c] - vb)
                for c in valid_combos
            }
        else:
            bet = _clip(_bet_bb(a, pot_bb, facing_bet), stack_bb)
            vr = _clip(3.0 * bet, stack_bb - bet)
            hc = (vr - bet) if vr > 0 else 0.0
            results[a] = {
                c: fp * (pot_bb + bet) + cp_pct * continuation[c]
                   + rp * max(0.0, continuation[c] - hc)
                   - bet
                for c in valid_combos
            }

    return results


def _solve_with_enumeration(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_actions: list[str],
    villain_range: dict[tuple[Card, Card], float],
    pot_bb: float,
    stack_bb: float,
    valid_combos: list[tuple[Card, Card]],
    hero_is_ip: bool,
    equity_cache: dict[tuple, dict],
    facing_bet: float,
) -> dict[str, dict[tuple[Card, Card], float]]:
    """Enumerate next-street cards with batched predictions."""
    next_street = NEXT_STREET.get(street, "river")
    deck = _remaining_deck(board)

    # 1. Batch model predictions: current street hero actions
    base = _build_sequence_tokens(board, action_prefix)
    cur_seqs: list[list[Token]] = []
    cur_keys: list[str] = []
    for a in hero_actions:
        if a == "Fold":
            continue
        cur_seqs.append(base + [_hero_token(a, pot_bb, facing_bet, stack_bb)])
        cur_keys.append(a)

    t0 = time.perf_counter()
    cur_probs = _batch_predict(model, cur_seqs, stack_bb)
    logger.info("Current-street batch: %d seqs in %.0fms",
                len(cur_seqs), (time.perf_counter() - t0) * 1000)

    # Parse current-street villain responses
    cur_villain: dict[str, tuple[float, float, float]] = {}
    for idx, a in enumerate(cur_keys):
        is_agg = a not in ("Check", "Call")
        cur_villain[a] = _villain_probs(cur_probs[idx], is_agg)

    # 2. Batch model predictions: next-street hero actions for each card
    future_seqs: list[list[Token]] = []
    future_keys: list[tuple[int, str]] = []  # (card_idx, action)

    for ci, card in enumerate(deck):
        new_board = board + [card]
        fb = _build_sequence_tokens(new_board, action_prefix)
        for a in HERO_OPEN_ACTIONS:
            if a == "Fold":
                continue
            future_seqs.append(fb + [_hero_token(a, pot_bb, 0.0, stack_bb)])
            future_keys.append((ci, a))

    t0 = time.perf_counter()
    future_probs = _batch_predict(model, future_seqs, stack_bb)
    logger.info("Future-street batch: %d seqs in %.0fms",
                len(future_seqs), (time.perf_counter() - t0) * 1000)

    # Build index: card_idx → {action: probs}
    card_prob_map: dict[int, dict[str, torch.Tensor]] = {}
    for batch_idx, (ci, a) in enumerate(future_keys):
        card_prob_map.setdefault(ci, {})[a] = future_probs[batch_idx]

    # 3. For each card, solve future street using pre-computed predictions
    continuation_sums: dict[tuple[Card, Card], float] = {c: 0.0 for c in valid_combos}
    continuation_counts: dict[tuple[Card, Card], int] = {c: 0 for c in valid_combos}

    for ci, card in enumerate(deck):
        new_board = board + [card]
        card_range = _remove_card_from_range(villain_range, card)
        cp = card_prob_map.get(ci, {})

        if next_street == "river":
            card_ev = _solve_turn_card(
                new_board, pot_bb, stack_bb, card_range,
                model, action_prefix, stack_bb,
                valid_combos, equity_cache, cp, card,
            )
        else:
            # Turn card on a flop solve — need to enumerate river too
            card_ev = _solve_turn_with_river_enum(
                new_board, pot_bb, stack_bb, card_range,
                model, action_prefix, stack_bb,
                valid_combos, equity_cache, cp, card, hero_is_ip,
            )

        for c in valid_combos:
            if not _card_in_combo(card, c):
                continuation_sums[c] += card_ev[c]
                continuation_counts[c] += 1

    # Average continuation values
    continuation: dict[tuple[Card, Card], float] = {}
    for c in valid_combos:
        if continuation_counts[c] > 0:
            continuation[c] = continuation_sums[c] / continuation_counts[c]
        else:
            continuation[c] = 0.0

    # 4. Combine current-street villain response with continuation EVs
    return _combine_continuation(
        hero_actions, cur_villain, continuation, valid_combos,
        pot_bb, facing_bet, stack_bb,
    )


def _solve_turn_with_river_enum(
    board_4: list[Card],
    pot_bb: float,
    stack: float,
    villain_range: dict[tuple[Card, Card], float],
    model: SolverTransformer,
    action_prefix: list[str],
    stack_bb: float,
    valid_combos: list[tuple[Card, Card]],
    equity_cache: dict[tuple, dict],
    turn_probs: dict[str, torch.Tensor],
    turn_card: Card,
    hero_is_ip: bool,
) -> dict[tuple[Card, Card], float]:
    """From a turn card during flop solve: enumerate river cards.

    turn_probs has villain predictions for turn hero actions (pre-computed).
    We need to batch-predict river hero actions for all river cards.
    """
    river_deck = _remaining_deck(board_4)

    # Batch river predictions: each river card × hero open actions
    river_seqs: list[list[Token]] = []
    river_keys: list[tuple[int, str]] = []

    for ri, rc in enumerate(river_deck):
        board_5 = board_4 + [rc]
        rb = _build_sequence_tokens(board_5, action_prefix)
        for a in HERO_OPEN_ACTIONS:
            if a == "Fold":
                continue
            river_seqs.append(rb + [_hero_token(a, pot_bb, 0.0, stack)])
            river_keys.append((ri, a))

    river_probs = _batch_predict(model, river_seqs, stack_bb)

    # Index river predictions
    river_prob_map: dict[int, dict[str, torch.Tensor]] = {}
    for bi, (ri, a) in enumerate(river_keys):
        river_prob_map.setdefault(ri, {})[a] = river_probs[bi]

    # Solve each river card
    ev_sums: dict[tuple[Card, Card], float] = {c: 0.0 for c in valid_combos}
    ev_counts: dict[tuple[Card, Card], int] = {c: 0 for c in valid_combos}

    for ri, rc in enumerate(river_deck):
        board_5 = board_4 + [rc]
        r_range = _remove_card_from_range(villain_range, rc)
        rp = river_prob_map.get(ri, {})

        card_ev = _solve_turn_card(
            board_5, pot_bb, stack, r_range,
            model, action_prefix, stack_bb,
            valid_combos, equity_cache, rp, rc,
        )

        for c in valid_combos:
            if not _card_in_combo(rc, c) and not _card_in_combo(turn_card, c):
                ev_sums[c] += card_ev[c]
                ev_counts[c] += 1

    # Average
    best_ev: dict[tuple[Card, Card], float] = {}
    for c in valid_combos:
        if ev_counts[c] > 0:
            best_ev[c] = ev_sums[c] / ev_counts[c]
        else:
            best_ev[c] = 0.0

    # Now combine with turn-level villain response using turn_probs
    # Hero picks best action on turn, weighted by villain response
    turn_best: dict[tuple[Card, Card], float] = {c: 0.0 for c in valid_combos}

    for action in HERO_OPEN_ACTIONS:
        if action == "Fold":
            continue
        probs = turn_probs.get(action)
        if probs is None:
            continue

        is_agg = action not in ("Check", "Call")
        fp, cp, rp = _villain_probs(probs, is_agg)
        bet = _clip(_bet_bb(action, pot_bb, 0.0), stack)

        if action == "Check":
            # check back → river continuation
            vb = _clip(VILLAIN_BET_SIZE * pot_bb, stack)
            for c in valid_combos:
                check_ev = cp * best_ev.get(c, 0.0)
                bet_branch = rp * max(0.0, best_ev.get(c, 0.0) - vb) if vb > 0 else 0.0
                ev = check_ev + bet_branch
                turn_best[c] = max(turn_best[c], ev)
        else:
            if bet <= 0:
                continue
            fold_ev = pot_bb + bet
            vr = _clip(3.0 * bet, stack - bet)
            hc = (vr - bet) if vr > 0 else 0.0
            for c in valid_combos:
                ev = (fp * fold_ev
                      + cp * best_ev.get(c, 0.0)
                      + rp * max(0.0, best_ev.get(c, 0.0) - hc)
                      - bet)
                turn_best[c] = max(turn_best[c], ev)

    return turn_best

def mc_solve_spot_streaming(
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
):
    """Generator yielding progress updates during solve."""
    t0 = time.perf_counter()
    equity_cache: dict[tuple, dict] = {}
    facing = _compute_facing_bet(action_prefix, pot_bb)

    if street == "river":
        result = _solve_river(
            board, pot_bb, starting_bb, hero_actions,
            villain_range, model, action_prefix,
            starting_bb, valid_combos, equity_cache,
            facing_bet=facing,
        )
        yield {
            "type": "complete", "progress": 1.0, "simsComplete": 1,
            "solveTime": round(time.perf_counter() - t0, 2),
            "combo_evs": _serialize(result, valid_combos),
        }
        return

    next_street = NEXT_STREET.get(street, "river")
    deck = _remaining_deck(board)
    random.shuffle(deck)

    # 1. Batch current-street predictions
    base = _build_sequence_tokens(board, action_prefix)
    cur_seqs = []
    cur_keys = []
    for a in hero_actions:
        if a == "Fold":
            continue
        cur_seqs.append(base + [_hero_token(a, pot_bb, facing, starting_bb)])
        cur_keys.append(a)

    cur_probs = _batch_predict(model, cur_seqs, starting_bb)
    cur_villain: dict[str, tuple[float, float, float]] = {}
    for idx, a in enumerate(cur_keys):
        is_agg = a not in ("Check", "Call")
        cur_villain[a] = _villain_probs(cur_probs[idx], is_agg)

    # 2. Batch next-street predictions for ALL cards
    future_seqs = []
    future_keys = []
    for ci, card in enumerate(deck):
        fb = _build_sequence_tokens(board + [card], action_prefix)
        for a in HERO_OPEN_ACTIONS:
            if a == "Fold":
                continue
            future_seqs.append(fb + [_hero_token(a, pot_bb, 0.0, starting_bb)])
            future_keys.append((ci, a))

    t_pred = time.perf_counter()
    future_probs = _batch_predict(model, future_seqs, starting_bb)
    logger.info("Batched %d next-street predictions in %.0fms",
                len(future_seqs), (time.perf_counter() - t_pred) * 1000)

    card_prob_map: dict[int, dict[str, torch.Tensor]] = {}
    for bi, (ci, a) in enumerate(future_keys):
        card_prob_map.setdefault(ci, {})[a] = future_probs[bi]

    yield {"type": "progress", "stage": "solving", "totalCards": len(deck)}

    # 3. Solve each card
    cont_sums: dict[tuple[Card, Card], float] = {c: 0.0 for c in valid_combos}
    cont_counts: dict[tuple[Card, Card], int] = {c: 0 for c in valid_combos}

    for ci, card in enumerate(deck):
        t_card = time.perf_counter()
        new_board = board + [card]
        card_range = _remove_card_from_range(villain_range, card)
        cp = card_prob_map.get(ci, {})

        if next_street == "river":
            card_ev = _solve_turn_card(
                new_board, pot_bb, starting_bb, card_range,
                model, action_prefix, starting_bb,
                valid_combos, equity_cache, cp, card,
            )
        else:
            card_ev = _solve_turn_with_river_enum(
                new_board, pot_bb, starting_bb, card_range,
                model, action_prefix, starting_bb,
                valid_combos, equity_cache, cp, card, hero_is_ip,
            )

        for c in valid_combos:
            if not _card_in_combo(card, c):
                cont_sums[c] += card_ev[c]
                cont_counts[c] += 1

        elapsed_card = time.perf_counter() - t_card
        cs = f"{card.rank.value}{card.suit.value}"
        logger.info("%s card %d/%d (%s) in %.2fs",
                    street, ci + 1, len(deck), cs, elapsed_card)

        # Compute running-average continuation and combine with villain probs
        running_cont = {
            c: cont_sums[c] / cont_counts[c] if cont_counts[c] > 0 else 0.0
            for c in valid_combos
        }
        running_evs = _combine_continuation(
            hero_actions, cur_villain, running_cont, valid_combos,
            pot_bb, facing, starting_bb,
        )

        progress = (ci + 1) / len(deck)
        yield {
            "type": "update",
            "progress": round(progress, 3),
            "simsComplete": ci + 1,
            "totalCards": len(deck),
            "combo_evs": _serialize(running_evs, valid_combos),
        }

    # Final result uses the same running EVs (all cards processed)
    elapsed = time.perf_counter() - t0
    yield {
        "type": "complete", "progress": 1.0,
        "simsComplete": len(deck),
        "solveTime": round(elapsed, 2),
        "combo_evs": _serialize(running_evs, valid_combos),
    }


def _serialize(
    evs: dict[str, dict[tuple[Card, Card], float]],
    valid_combos: list[tuple[Card, Card]],
) -> dict[str, dict[str, float]]:
    out = {}
    for a, cev in evs.items():
        out[a] = {}
        for c in valid_combos:
            cs = f"{c[0].rank.value}{c[0].suit.value}{c[1].rank.value}{c[1].suit.value}"
            out[a][cs] = round(cev.get(c, 0.0), 2)
    return out
