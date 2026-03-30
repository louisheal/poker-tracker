import hashlib

from fastapi import APIRouter, Query

router = APIRouter()

RANKS = "A K Q J T 9 8 7 6 5 4 3 2".split()
SUITS = ["h", "d", "s", "c"]


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
        # Pair: e.g. AA -> AhAd, AhAs, AhAc, AdAs, AdAc, AsAc
        r = key[0]
        combos = []
        for i, s1 in enumerate(SUITS):
            for s2 in SUITS[i + 1:]:
                combos.append(f"{r}{s1}{r}{s2}")
        return combos
    elif key.endswith("s"):
        # Suited: e.g. AKs -> AhKh, AdKd, AsKs, AcKc
        r1, r2 = key[0], key[1]
        return [f"{r1}{s}{r2}{s}" for s in SUITS]
    else:
        # Offsuit: e.g. AKo -> 12 combos
        r1, r2 = key[0], key[1]
        combos = []
        for s1 in SUITS:
            for s2 in SUITS:
                if s1 != s2:
                    combos.append(f"{r1}{s1}{r2}{s2}")
        return combos


def _seeded_float(seed: str, low: float, high: float) -> float:
    """Deterministic float from a seed string."""
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    t = (h % 10000) / 10000
    return low + t * (high - low)


def _hand_strength(key: str) -> float:
    """Rough hand strength heuristic for plausible mock data."""
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


@router.get("/solve")
def solve_mock(
    board: list[str] = Query(default=[]),
    street: str = Query(default="preflop"),
    actions: list[str] = Query(default=[]),
):
    """Mock solver endpoint returning deterministic plausible data."""
    context_seed = f"{''.join(sorted(board))}_{street}_{'|'.join(actions)}"

    # Determine which action set to use based on street/context
    last_action = actions[-1].split(":")[-1] if actions else ""
    is_facing_bet = last_action.startswith("B") or last_action.startswith("R")

    if street == "preflop":
        if any(":Raise" in a for a in actions):
            action_keys = ["Fold", "Call", "Raise"]
        else:
            action_keys = ["Fold", "Call", "Raise"]
    elif is_facing_bet:
        action_keys = ["Fold", "Call", "R3x", "R4x", "R5x"]
    else:
        action_keys = ["Check", "B33", "B50", "B66", "B100", "B133", "B200"]

    hands: dict = {}
    action_counts: dict[str, int] = {a: 0 for a in action_keys}
    action_ev_sums: dict[str, float] = {a: 0.0 for a in action_keys}

    for key in _hand_keys():
        strength = _hand_strength(key)
        evs: dict[str, float] = {}

        for i, action in enumerate(action_keys):
            seed = f"{context_seed}_{key}_{action}"
            noise = _seeded_float(seed, -2.0, 2.0)

            # Spread EVs based on action aggressiveness
            aggression = i / max(len(action_keys) - 1, 1)
            ev = (strength - 0.3 - aggression * 0.2) * (8 + aggression * 8) + noise
            evs[action] = round(ev, 2)

        best = max(evs, key=lambda k: evs[k])
        
        # Generate combo-level data with per-action EVs
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
