from __future__ import annotations

from app.parsers.equity import VALID_TRIPLES, HandTriple


DEFAULT_MEDIAN_RAISE_MULTIPLIER = 3
DEFAULT_RAISE_MULTIPLIER = 3


def calculate_ev_open(
    node_data: dict,
    bet_sizes: list[float],
) -> dict:
    """Compute EV(action | hero_triple) when hero acts first (check or bet).

    Uses precomputed equity dicts from ev_node_data().

    Returns:
        {
            "rows": [
                {
                    "made": "SET",
                    "flush_draw": "NONE",
                    "straight_draw": "NONE",
                    "evs": {"X": 12.5, "B33": 14.2, ...},
                    "best_action": "B66",
                },
                ...
            ],
            "available_actions": ["X", "B33", "B66", ...],
        }
    """
    pot: float = node_data["pot_bb"]
    fold_pct, call_pct, raise_pct = _reaction_pcts(node_data)

    equity_vs_full: dict[HandTriple, float] = node_data["equity_vs_full"]
    equity_vs_call: dict[HandTriple, float] = node_data["equity_vs_call"]
    equity_vs_raise: dict[HandTriple, float] = node_data["equity_vs_raise"]

    median_raise: float | None = node_data["median_raise_size_pct"]

    rows: list[dict] = []
    for hero_triple in VALID_TRIPLES:
        eq_full: float = equity_vs_full[hero_triple]
        eq_call: float = equity_vs_call[hero_triple]
        eq_raise: float = equity_vs_raise[hero_triple]

        evs: dict[str, float] = {}

        # EV(check) = equity vs full range x pot
        evs["X"] = round(eq_full * pot, 2)

        for size_pct in bet_sizes:
            bet_bb: float = (size_pct / 100) * pot
            call_pot: float = pot + 2 * bet_bb

            raise_pct_size: float = (
                (median_raise or DEFAULT_MEDIAN_RAISE_MULTIPLIER * size_pct)
                + DEFAULT_MEDIAN_RAISE_MULTIPLIER * size_pct
            ) / 2
            raise_bb: float = (raise_pct_size / 100) * pot
            raise_pot: float = pot + bet_bb + 2 * raise_bb

            ev: float = (
                fold_pct * pot
                + call_pct * (eq_call * call_pot - bet_bb)
                + raise_pct * (eq_raise * raise_pot - raise_bb)
            )

            evs[f"B{size_pct}"] = round(ev, 2)

        best_action: str = max(evs, key=lambda k: evs[k])

        rows.append({
            "made": hero_triple[0].value,
            "flush_draw": hero_triple[1].value,
            "straight_draw": hero_triple[2].value,
            "evs": evs,
            "best_action": best_action,
        })

    return {
        "rows": rows,
        "available_actions": ["X"] + [f"B{s}" for s in bet_sizes],
    }


def calculate_ev_vs_bet(
    node_data: dict,
    villain_bet_bb: float,
) -> dict:
    """Compute EV(action | hero_triple) when hero faces a bet or raise.

    Options: Fold / Call / Raise (3x the bet).
    Also reusable vs a raise: set pot = original_pot + 2 x hero_bet,
    villain_bet_bb = raise_total - hero_bet.

    Returns:
        {
            "rows": [
                {
                    "made": "SET",
                    "flush_draw": "NONE",
                    "straight_draw": "NONE",
                    "evs": {"F": 0, "C": 4.2, "R": 6.1},
                    "best_action": "R",
                },
                ...
            ],
            "available_actions": ["F", "C", "R"],
        }
    """
    pot: float = node_data["pot_bb"]
    fold_pct, call_pct, raise_pct = _reaction_pcts(node_data)

    equity_vs_call: dict[HandTriple, float] = node_data["equity_vs_call"]
    equity_vs_raise: dict[HandTriple, float] = node_data["equity_vs_raise"]

    call_pot: float = pot + 2 * villain_bet_bb
    raise_total_bb: float = villain_bet_bb * DEFAULT_RAISE_MULTIPLIER
    raise_cost: float = raise_total_bb
    raise_call_pot: float = pot + villain_bet_bb + 2 * raise_total_bb

    rows: list[dict] = []
    for hero_triple in VALID_TRIPLES:
        eq_call: float = equity_vs_call[hero_triple]
        eq_raise: float = equity_vs_raise[hero_triple]

        evs: dict[str, float] = {}

        # EV(fold) = 0 — hero loses nothing more
        evs["F"] = 0.0

        # EV(call) = equity x total pot after call - cost to call
        evs["C"] = round(eq_call * call_pot - villain_bet_bb, 2)

        # EV(raise 3x) = villain folds: win pot + their bet
        #              + villain calls: equity x pot - raise cost
        #              + villain re-raises: simplified as call equity
        evs["R"] = round(
            fold_pct * (pot + villain_bet_bb)
            + call_pct * (eq_call * raise_call_pot - raise_cost)
            + raise_pct * (eq_raise * raise_call_pot - raise_cost),
            2,
        )

        best_action: str = max(evs, key=lambda k: evs[k])

        rows.append({
            "made": hero_triple[0].value,
            "flush_draw": hero_triple[1].value,
            "straight_draw": hero_triple[2].value,
            "evs": evs,
            "best_action": best_action,
        })

    return {
        "rows": rows,
        "available_actions": ["F", "C", "R"],
    }


def _reaction_pcts(node_data: dict) -> tuple[float, float, float]:
    """Extract fold/call/raise percentages from node_data."""
    fold_count: int = node_data["fold_count"]
    call_count: int = node_data["call_count"]
    raise_count: int = node_data["raise_count"]
    total: int = fold_count + call_count + raise_count

    fold_pct: float = fold_count / total if total else 0
    call_pct: float = call_count / total if total else 0
    raise_pct: float = raise_count / total if total else 0

    return fold_pct, call_pct, raise_pct
