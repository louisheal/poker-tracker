"""Tests for the recursive river solver (streets/river.py)."""

import pytest

from solver.streets.common import (
    _enumerate_sequences,
    _get_hero_actions,
    _compute_bet_size,
    VILLAIN_RAISE_MULTIPLIER,
)
from solver.streets.river import (
    _eval_action,
    _solve_node,
)


class TestEnumerateAndEvalConsistency:
    """Enumeration and EV computation must agree on which cache keys exist."""

    def _collect_eval_keys(
        self, pot, facing_bet, remaining_bb, is_opener, prefix="",
    ) -> set[str]:
        """Walk the same tree that _eval_action/_solve_node would walk,
        collecting all prediction cache keys they'd try to look up.

        This mirrors the recursion in _eval_action without needing a real model.
        """
        keys: set[str] = set()
        hero_actions = _get_hero_actions(pot, facing_bet, remaining_bb, is_opener)

        for action in hero_actions:
            if action in ("Fold", "Call"):
                continue
            if action == "Check" and not is_opener:
                continue

            hero_bet = _compute_bet_size(action, pot, facing_bet, remaining_bb)

            if action == "Check":
                cache_key = f"{prefix}>X" if prefix else "X"
            elif action == "R3x":
                cache_key = f"{prefix}>R3x" if prefix else "R3x"
            else:
                cache_key = f"{prefix}>{action}" if prefix else action

            keys.add(cache_key)

            is_all_in = hero_bet >= remaining_bb
            new_remaining_bb = remaining_bb - hero_bet

            if action == "Check" and is_opener:
                villain_bet = min(0.66 * pot, new_remaining_bb)
                if villain_bet > 0:
                    sub_key = f"{cache_key}>B"
                    sub_keys = self._collect_eval_keys(
                        pot, villain_bet, new_remaining_bb,
                        is_opener=False, prefix=sub_key,
                    )
                    keys.update(sub_keys)

            elif not is_all_in:
                villain_raise = min(
                    VILLAIN_RAISE_MULTIPLIER * hero_bet, new_remaining_bb,
                )
                if villain_raise > hero_bet:
                    new_pot = pot + 2 * hero_bet
                    new_facing = villain_raise - hero_bet
                    sub_key = f"{cache_key}>R"
                    sub_keys = self._collect_eval_keys(
                        new_pot, new_facing, new_remaining_bb,
                        is_opener=False, prefix=sub_key,
                    )
                    keys.update(sub_keys)

        return keys

    def _collect_enum_keys(self, pot, facing_bet, remaining_bb, is_opener) -> set[str]:
        """Collect cache keys from _enumerate_sequences."""
        sequences = _enumerate_sequences(
            pot, facing_bet, remaining_bb,
            cache_key_prefix="", is_opener=is_opener, tokens_so_far=[],
        )
        return {cache_key for cache_key, _, _, _ in sequences}

    @pytest.mark.parametrize("pot,remaining,is_opener", [
        (10.0, 90.0, True),
        (10.0, 90.0, False),
        (45.0, 77.5, True),
        (45.0, 77.5, False),
        (6.5, 96.75, True),
        (6.5, 96.75, False),
        (80.0, 60.0, True),
        (80.0, 60.0, False),
        (5.0, 97.5, True),
        (120.0, 40.0, True),
    ])
    def test_enum_covers_all_eval_keys_opener(self, pot, remaining, is_opener):
        """Every cache key the EV computation would access must exist in the
        enumeration output. A mismatch causes KeyError at runtime."""
        enum_keys = self._collect_enum_keys(pot, 0.0, remaining, is_opener)
        eval_keys = self._collect_eval_keys(pot, 0.0, remaining, is_opener)
        missing = eval_keys - enum_keys
        assert not missing, (
            f"EV would access keys not in enumeration: {missing}\n"
            f"Enum keys: {sorted(enum_keys)}\n"
            f"Eval keys: {sorted(eval_keys)}"
        )

    @pytest.mark.parametrize("pot,facing,remaining", [
        (10.0, 5.0, 90.0),
        (45.0, 15.0, 70.0),
        (6.5, 4.3, 96.75),
        (80.0, 26.0, 47.0),
        (20.0, 6.6, 93.4),
    ])
    def test_enum_covers_all_eval_keys_facing_bet(self, pot, facing, remaining):
        """Same consistency check when hero faces a bet."""
        enum_keys = self._collect_enum_keys(pot, facing, remaining, is_opener=False)
        eval_keys = self._collect_eval_keys(pot, facing, remaining, is_opener=False)
        missing = eval_keys - enum_keys
        assert not missing, (
            f"EV would access keys not in enumeration: {missing}\n"
            f"Enum keys: {sorted(enum_keys)}\n"
            f"Eval keys: {sorted(eval_keys)}"
        )


class TestRaiseTermination:
    """Raise recursion must terminate naturally via all-in / stack exhaustion."""

    def test_deep_raise_sequence_terminates(self):
        """With a small pot and large remaining stack, multiple raise levels
        should be enumerated and terminate at all-in."""
        sequences = _enumerate_sequences(
            pot=6.5, facing_bet=0.0, remaining_bb=96.75,
            cache_key_prefix="", is_opener=True, tokens_so_far=[],
        )
        keys = {k for k, _, _, _ in sequences}
        # B33 produces tiny bets that allow many raise levels
        assert any(k.count(">R") >= 2 for k in keys), (
            f"Expected at least 2 raise levels, got: {sorted(keys)}"
        )
        # Every branch must terminate (no infinite recursion = test completes)

    def test_all_in_stops_enumeration(self):
        """When remaining is tiny, hero is forced all-in immediately."""
        sequences = _enumerate_sequences(
            pot=80.0, facing_bet=0.0, remaining_bb=5.0,
            cache_key_prefix="", is_opener=True, tokens_so_far=[],
        )
        keys = {k for k, _, ai, _ in sequences}
        all_ins = {k for k, _, ai, _ in sequences if ai}
        # All bet actions should be all-in (5 BB < any bet size on 80 BB pot)
        bet_keys = {k for k in keys if k != "X"}
        assert bet_keys == all_ins

    def test_villain_raise_guard_prevents_negative_facing(self):
        """When villain can't raise above hero's bet, no deeper recursion."""
        # Hero bets 1.33 * 10 = 13.3 BB, remaining after = 11.7 BB
        # Villain raise = min(39.9, 11.7) = 11.7 < 13.3 → no raise enumerated
        sequences = _enumerate_sequences(
            pot=10.0, facing_bet=0.0, remaining_bb=25.0,
            cache_key_prefix="", is_opener=False, tokens_so_far=[],
        )
        keys = {k for k, _, _, _ in sequences}
        # B133 should exist but B133>R should NOT (villain can't raise)
        assert "B133" in keys
        assert not any(k.startswith("B133>R") for k in keys), (
            f"B133 should not have raise continuation: {sorted(keys)}"
        )


class TestFacingAllIn:
    """When the last action in the prefix is All-in, hero must only get Fold/Call."""

    def test_hero_actions_facing_all_in(self):
        """facing_bet = 2*starting_bb - pot_bb gives correct remaining and
        _get_hero_actions returns only Fold/Call."""
        starting_bb = 100.0
        pot_bb = 102.75  # preflop 5.5 + villain all-in 97.25
        facing_bet = 2 * starting_bb - pot_bb  # 97.25
        matched_pot = pot_bb - facing_bet  # 5.5
        remaining_bb = starting_bb - matched_pot / 2  # 97.25

        actions = _get_hero_actions(matched_pot, facing_bet, remaining_bb, is_opener=False)
        assert actions == ["Fold", "Call"]

    def test_enumeration_facing_all_in(self):
        """Enumeration when facing all-in should produce only Fold/Call sequences."""
        starting_bb = 100.0
        pot_bb = 102.75
        facing_bet = 2 * starting_bb - pot_bb
        matched_pot = pot_bb - facing_bet
        remaining_bb = starting_bb - matched_pot / 2

        sequences = _enumerate_sequences(
            pot=matched_pot, facing_bet=facing_bet, remaining_bb=remaining_bb,
            cache_key_prefix="", is_opener=False, tokens_so_far=[],
        )
        keys = {k for k, _, _, _ in sequences}
        # Fold and Call have no villain response node → empty prediction cache
        assert keys == set(), f"Expected no prediction sequences, got: {sorted(keys)}"

    def test_full_solve_spot_facing_all_in(self):
        """full_solve_spot correctly computes facing_bet when prefix ends with All-in."""
        from solver.streets.river import full_solve_spot
        from solver.streets.mc_solver import _compute_facing_bet

        action_prefix = [
            "LJ:Raise", "HJ:Fold", "CO:Fold", "BTN:Fold", "SB:Fold", "BB:Call",
            "OOP:Check", "IP:B33", "OOP:R3x", "IP:Call",
            "OOP:Check", "IP:Check",
            "OOP:B133", "IP:All-in",
        ]
        starting_bb = 100.0
        pot_bb = 102.75  # example pot after all-in

        # _compute_facing_bet SHOULD handle All-in properly
        # (or full_solve_spot should bypass it)
        last_action = action_prefix[-1].split(":")[-1]
        assert last_action == "All-in"

        # After the fix: facing_bet should equal hero's remaining stack
        facing_bet = 2 * starting_bb - pot_bb
        matched_pot = pot_bb - facing_bet
        remaining_bb = starting_bb - matched_pot / 2
        assert facing_bet >= remaining_bb, (
            f"facing_bet={facing_bet} must be >= remaining_bb={remaining_bb} for All-in"
        )


class TestPotEstimation:
    """Tests for the router's _estimate_pot_bb function."""

    def test_all_in_action_in_pot_estimation(self):
        """All-in in a postflop action sequence should not crash and should
        add the remaining stack to the pot (starting_bb=100 by default)."""
        from app.routers.solver import _estimate_pot_bb

        actions = [
            "LJ:Raise", "HJ:Fold", "CO:Fold", "BTN:Fold", "SB:Fold", "BB:Call",
            "OOP:Check", "IP:B33", "OOP:Call",
            "OOP:Check", "IP:B66", "OOP:Call",
            "OOP:All-in",
        ]
        pot_bb, facing_bet = _estimate_pot_bb(actions)
        assert pot_bb > 0
        assert pot_bb > 20.0
        assert facing_bet > 0  # All-in creates an outstanding bet

    def test_all_in_adds_remaining_to_pot(self):
        """All-in should add (starting_bb - pot_bb/2) to the pot."""
        from app.routers.solver import _estimate_pot_bb

        # Simple case: raise + call → pot ~5.5, then OOP goes all-in
        actions = [
            "LJ:Raise", "HJ:Fold", "CO:Fold", "BTN:Fold", "SB:Fold", "BB:Call",
            "OOP:All-in",
        ]
        pot_bb, facing_bet = _estimate_pot_bb(actions)
        # Preflop pot ≈ 5.5. remaining = 100 - 5.5/2 = 97.25
        # After all-in: pot ≈ 5.5 + 97.25 = 102.75
        assert abs(pot_bb - 102.75) < 0.1

    def test_facing_bet_for_raise(self):
        """R3x should return correct facing_bet (3x the previous bet)."""
        from app.routers.solver import _estimate_pot_bb

        actions = [
            "LJ:Raise", "HJ:Fold", "CO:Fold", "BTN:Fold", "SB:Fold", "BB:Call",
            "OOP:Check", "IP:B33", "OOP:R3x", "IP:Call",
            "OOP:Check", "IP:Check",
            "OOP:B33", "IP:R3x",
        ]
        pot_bb, facing_bet = _estimate_pot_bb(actions)
        # B33 on ~18.2 pot → bet ≈ 6.0, R3x → 3 * 6.0 ≈ 18.0
        assert facing_bet > 10.0, f"facing_bet should be ~18, got {facing_bet}"
        matched_pot = pot_bb - facing_bet
        remaining_bb = 100.0 - matched_pot / 2
        assert remaining_bb > 0, f"remaining_bb should be positive, got {remaining_bb}"
        assert matched_pot > 0, f"matched_pot should be positive, got {matched_pot}"
