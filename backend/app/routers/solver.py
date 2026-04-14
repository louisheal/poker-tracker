import hashlib
import logging
import os

from fastapi import APIRouter, Query, Request

router = APIRouter()

logger = logging.getLogger(__name__)

RANKS = "A K Q J T 9 8 7 6 5 4 3 2".split()
SUITS = ["h", "d", "s", "c"]

# Action key -> bet size as pct of pot (for pot_bb calculation)
_ACTION_BET_PCT: dict[str, float] = {
    "Fold": 0, "Check": 0, "Call": 0, "Raise": 300,
    "B33": 33, "B50": 50, "B66": 66, "B100": 100, "B133": 133, "B200": 200,
}

# Postflop raises: N× the previous bet (not pot %)
_RAISE_MULTIPLIER: dict[str, float] = {
    "R3x": 3.0, "R4x": 4.0, "R5x": 5.0,
}


def _hand_keys() -> list[str]:
    """Generate all 169 distinct starting hand keys."""
    keys = []
    for i, r1 in enumerate(RANKS):
        for j, r2 in enumerate(RANKS):
            if i == j:
                keys.append(f"{r1}{r2}")
            elif i < j:
                keys.append(f"{r1}{r2}s")
            else:
                keys.append(f"{r2}{r1}o")
    return keys


def _combos_for_key(key: str) -> list[str]:
    """Generate all specific combos for a hand key."""
    if len(key) == 2:
        r = key[0]
        combos = []
        for i, s1 in enumerate(SUITS):
            for s2 in SUITS[i + 1:]:
                combos.append(f"{r}{s1}{r}{s2}")
        return combos
    elif key.endswith("s"):
        r1, r2 = key[0], key[1]
        return [f"{r1}{s}{r2}{s}" for s in SUITS]
    else:
        r1, r2 = key[0], key[1]
        combos = []
        for s1 in SUITS:
            for s2 in SUITS:
                if s1 != s2:
                    combos.append(f"{r1}{s1}{r2}{s2}")
        return combos


def _seeded_float(seed: str, low: float, high: float) -> float:
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    t = (h % 10000) / 10000
    return low + t * (high - low)


def _hand_strength(key: str) -> float:
    rank_values = {r: i for i, r in enumerate(reversed(RANKS))}
    r1 = rank_values.get(key[0], 0)
    r2 = rank_values.get(key[1], 0)
    is_pair = len(key) == 2 or (len(key) == 3 and key[0] == key[1])
    is_suited = key.endswith("s")
    strength = (r1 + r2) / 24
    if is_pair:
        strength += 0.3
    if is_suited:
        strength += 0.08
    if abs(r1 - r2) <= 2 and not is_pair:
        strength += 0.05
    return min(strength, 1.0)


def _detect_action_keys(street: str, actions: list[str]) -> list[str]:
    """Determine which action set to use based on street/context."""
    last_action = actions[-1].split(":")[-1] if actions else ""
    is_facing_bet = last_action.startswith("B") or last_action.startswith("R")

    if street == "preflop":
        return ["Fold", "Call", "Raise"]
    elif is_facing_bet:
        return ["Fold", "Call", "R3x", "R4x", "R5x"]
    else:
        return ["Check", "B33", "B50", "B66", "B100", "B133", "B200"]


def _solve_mock(board: list[str], street: str, actions: list[str]) -> dict:
    """Mock solver: returns deterministic plausible data when no model is loaded."""
    context_seed = f"{''.join(sorted(board))}_{street}_{'|'.join(actions)}"
    action_keys = _detect_action_keys(street, actions)

    hands: dict = {}
    action_counts: dict[str, int] = {a: 0 for a in action_keys}
    action_ev_sums: dict[str, float] = {a: 0.0 for a in action_keys}

    for key in _hand_keys():
        strength = _hand_strength(key)
        evs: dict[str, float] = {}

        for i, action in enumerate(action_keys):
            seed = f"{context_seed}_{key}_{action}"
            noise = _seeded_float(seed, -2.0, 2.0)
            aggression = i / max(len(action_keys) - 1, 1)
            ev = (strength - 0.3 - aggression * 0.2) * (8 + aggression * 8) + noise
            evs[action] = round(ev, 2)

        best = max(evs, key=lambda k: evs[k])

        combos = []
        for combo in _combos_for_key(key):
            combo_seed = f"{context_seed}_{combo}"
            combo_noise = _seeded_float(combo_seed, -1.5, 1.5)
            combo_evs = {}
            for j, a in enumerate(action_keys):
                combo_evs[a] = round(evs[a] + combo_noise * (0.5 + 0.2 * j), 2)
            combo_best = max(combo_evs, key=lambda k: combo_evs[k])
            combos.append({
                "combo": combo,
                "bestAction": combo_best,
                "ev": combo_evs[combo_best],
                "evs": combo_evs,
            })

        hands[key] = {"bestAction": best, "evs": evs, "combos": combos}

        # Compute per-combo actionCounts for this hand key
        combo_action_counts: dict[str, int] = {}
        for c in combos:
            ba = c["bestAction"]
            combo_action_counts[ba] = combo_action_counts.get(ba, 0) + 1
        hands[key]["actionCounts"] = combo_action_counts

        action_counts[best] += 1
        action_ev_sums[best] += evs[best]

    total = len(hands)
    result_actions: dict = {}
    for a in action_keys:
        seed = f"{context_seed}_{a}"
        fold_base = 30.0 + _seeded_float(seed + "_f", 0, 20)
        call_base = 40.0 + _seeded_float(seed + "_c", 0, 15)
        fold_pct = round(fold_base + _seeded_float(seed + "_f2", -5, 5), 1)
        call_pct = round(call_base + _seeded_float(seed + "_c2", -5, 5), 1)
        raise_pct = round(max(100 - fold_pct - call_pct, 5), 1)
        count = action_counts[a]
        avg_ev = round(action_ev_sums[a] / count, 2) if count > 0 else 0.0
        result_actions[a] = {
            "villainFoldPct": fold_pct,
            "villainCallPct": call_pct,
            "villainRaisePct": raise_pct,
            "avgEv": avg_ev,
            "bestActionCount": count,
        }

    return {"hands": hands, "actions": result_actions, "totalHands": total}


POSTFLOP_POSITION_ORDER = ["SB", "BB", "LJ", "HJ", "CO", "BTN"]


def _parse_preflop_context(actions: list[str]) -> dict:
    """Parse preflop actions to determine active players, pot type, and positions."""
    active: list[str] = []
    raise_count = 0

    for action_str in actions:
        parts = action_str.split(":")
        if len(parts) < 2:
            continue
        label, action_key = parts[0], parts[1]
        if label in ("OOP", "IP"):
            break
        if action_key != "Fold":
            if label not in active:
                active.append(label)
        if action_key == "Raise":
            raise_count += 1

    if raise_count >= 3:
        pot_type = "4BET"
    elif raise_count >= 2:
        pot_type = "3BET"
    else:
        pot_type = "SRP"

    # Determine OOP/IP by position order (earlier = OOP)
    active_sorted = sorted(
        active,
        key=lambda p: POSTFLOP_POSITION_ORDER.index(p) if p in POSTFLOP_POSITION_ORDER else 0,
    )
    oop = active_sorted[0] if active_sorted else "BB"
    ip = active_sorted[1] if len(active_sorted) > 1 else "BTN"

    return {
        "active_players": active,
        "pot_type": pot_type,
        "oop_position": oop,
        "ip_position": ip,
    }


def _solve_real(
    request: Request,
    board: list[str],
    street: str,
    actions: list[str],
    hero_position: str | None = None,
) -> dict:
    """Real solver: uses the trained model for villain predictions."""
    from app.parsers.lexer import to_card
    from solver.ev_calculator import solve_spot

    model = request.app.state.solver_model
    board_cards = [to_card(c) for c in board]

    action_keys = _detect_action_keys(street, actions)

    ctx = _parse_preflop_context(actions)
    pot_type = ctx["pot_type"]
    oop_pos = ctx["oop_position"]
    ip_pos = ctx["ip_position"]

    # Determine hero from parameter or infer from action count
    if not hero_position:
        postflop_count = sum(1 for a in actions if a.split(":")[0] in ("OOP", "IP"))
        hero_position = oop_pos if postflop_count % 2 == 0 else ip_pos

    villain_position = ip_pos if hero_position == oop_pos else oop_pos

    # Estimate pot size from the action prefix.
    # Preflop amounts are in BB (not pot-relative); postflop uses pot %.
    pot_bb = 1.5  # SB + BB
    in_preflop = True
    prev_raise_total = 0.0
    last_postflop_bet = 0.0
    for a in actions:
        parts = a.split(":")
        label = parts[0] if len(parts) > 1 else ""
        act = parts[-1] if len(parts) > 1 else parts[0]

        if label in ("OOP", "IP"):
            in_preflop = False

        if in_preflop:
            if act == "Raise":
                # Standard open: ~2.5BB total, 3bet: ~3x last raise
                pot_bb += max(2.5, prev_raise_total * 3) - prev_raise_total
                prev_raise_total = max(2.5, prev_raise_total * 3)
            elif act == "Call":
                pot_bb += max(prev_raise_total - 1.0, 1.0)
        else:
            pct = _ACTION_BET_PCT.get(act, 0)
            mult = _RAISE_MULTIPLIER.get(act, 0)
            if mult > 0 and last_postflop_bet > 0:
                # Raise = N× the previous bet
                raise_amount = mult * last_postflop_bet
                pot_bb += raise_amount
                last_postflop_bet = raise_amount
            elif pct > 0:
                bet_amount = (pct / 100.0) * pot_bb
                pot_bb += bet_amount
                last_postflop_bet = bet_amount
            elif act == "Call" and last_postflop_bet > 0:
                pot_bb += last_postflop_bet
                last_postflop_bet = 0

    return solve_spot(
        model=model,
        board=board_cards,
        street=street if board_cards else "preflop",
        action_prefix=actions,
        hero_position=hero_position,
        villain_position=villain_position,
        pot_type=pot_type,
        pot_bb=pot_bb,
        hero_actions=action_keys,
        effective_stack_bb=100.0,
    )


@router.get("/solve")
def solve(
    request: Request,
    board: list[str] = Query(default=[]),
    street: str = Query(default="preflop"),
    actions: list[str] = Query(default=[]),
    hero_position: str | None = Query(default=None),
):
    """Solver endpoint. Uses real model if loaded, otherwise falls back to mock."""
    has_model = hasattr(request.app.state, "solver_model") and request.app.state.solver_model is not None

    if has_model:
        return _solve_real(request, board, street, actions, hero_position)
    else:
        return _solve_mock(board, street, actions)


@router.get("/solve-stream")
async def solve_stream(
    request: Request,
    board: list[str] = Query(default=[]),
    street: str = Query(default="preflop"),
    actions: list[str] = Query(default=[]),
    hero_position: str | None = Query(default=None),
):
    """SSE endpoint that streams solver results as they compute."""
    import json
    from starlette.responses import StreamingResponse

    has_model = hasattr(request.app.state, "solver_model") and request.app.state.solver_model is not None

    if not has_model:
        result = _solve_mock(board, street, actions)

        async def single():
            yield f"data: {json.dumps({'type': 'complete', **result})}\n\n"

        return StreamingResponse(single(), media_type="text/event-stream")

    from app.parsers.lexer import to_card
    from solver.mc_solver import mc_solve_spot_streaming
    from solver.ev_calculator import (
        compute_current_ranges, _determine_oop_ip,
        ACTION_TO_BET_PCT, RAISE_MULTIPLIER,
    )
    from solver.ranges import _cards_conflict

    model = request.app.state.solver_model
    board_cards = [to_card(c) for c in board]

    action_keys = _detect_action_keys(street, actions)
    ctx = _parse_preflop_context(actions)
    pot_type = ctx["pot_type"]
    oop_pos = ctx["oop_position"]
    ip_pos = ctx["ip_position"]

    if not hero_position:
        postflop_count = sum(1 for a in actions if a.split(":")[0] in ("OOP", "IP"))
        hero_position = oop_pos if postflop_count % 2 == 0 else ip_pos

    villain_position = ip_pos if hero_position == oop_pos else oop_pos
    hero_is_ip = hero_position == ip_pos

    # Estimate pot
    pot_bb = 1.5
    in_preflop = True
    prev_raise_total = 0.0
    last_postflop_bet = 0.0
    for a in actions:
        parts = a.split(":")
        label = parts[0] if len(parts) > 1 else ""
        act = parts[-1] if len(parts) > 1 else parts[0]
        if label in ("OOP", "IP"):
            in_preflop = False
        if in_preflop:
            if act == "Raise":
                pot_bb += max(2.5, prev_raise_total * 3) - prev_raise_total
                prev_raise_total = max(2.5, prev_raise_total * 3)
            elif act == "Call":
                pot_bb += max(prev_raise_total - 1.0, 1.0)
        else:
            pct = _ACTION_BET_PCT.get(act, 0)
            mult = _RAISE_MULTIPLIER.get(act, 0)
            if mult > 0 and last_postflop_bet > 0:
                raise_amount = mult * last_postflop_bet
                pot_bb += raise_amount
                last_postflop_bet = raise_amount
            elif pct > 0:
                bet_amount = (pct / 100.0) * pot_bb
                pot_bb += bet_amount
                last_postflop_bet = bet_amount
            elif act == "Call" and last_postflop_bet > 0:
                pot_bb += last_postflop_bet
                last_postflop_bet = 0

    effective_stack_bb = 100.0

    # Compute ranges
    from solver.ranges import ALL_COMBOS
    hero_range, villain_range = compute_current_ranges(
        model, board_cards, street if board_cards else "preflop", actions,
        hero_position, villain_position, pot_type, effective_stack_bb,
    )
    valid_combos = [c for c in ALL_COMBOS if not _cards_conflict(c, board_cards)]

    async def generate():
        for update in mc_solve_spot_streaming(
            model=model,
            board=board_cards,
            street=street if board_cards else "preflop",
            action_prefix=actions,
            hero_actions=action_keys,
            villain_range=villain_range,
            pot_bb=pot_bb,
            effective_stack_bb=effective_stack_bb,
            valid_combos=valid_combos,
            hero_is_ip=hero_is_ip,
        ):
            yield f"data: {json.dumps(update)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
