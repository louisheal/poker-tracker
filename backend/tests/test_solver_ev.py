"""Tests for solver EV formula helpers (one-level lookahead)."""

import pytest

from solver.ev_calculator import compute_check_ev, compute_aggressive_ev


class TestComputeCheckEv:
    """Test the Check EV formula with villain continuation."""

    def test_pure_showdown_when_villain_always_checks_back(self):
        """If villain never bets, Check EV = equity × pot (classic formula)."""
        ev = compute_check_ev(
            pot_bb=10.0,
            check_back_pct=1.0,
            villain_bet_pct=0.0,
            eq_vs_checking=0.6,
            eq_vs_betting=0.0,
            v_bet_bb=6.6,
        )
        assert ev == pytest.approx(6.0)

    def test_strong_hand_calls_villain_bet(self):
        """Strong hand (high equity vs betting range) should call profitably."""
        ev = compute_check_ev(
            pot_bb=10.0,
            check_back_pct=0.8,
            villain_bet_pct=0.2,
            eq_vs_checking=0.9,
            eq_vs_betting=0.85,
            v_bet_bb=6.6,
        )
        # check_back: 0.8 * 0.9 * 10 = 7.2
        # call_ev: 0.85 * (10 + 13.2) - 6.6 = 0.85 * 23.2 - 6.6 = 19.72 - 6.6 = 13.12
        # facing_bet: max(0, 13.12) = 13.12
        # total: 7.2 + 0.2 * 13.12 = 7.2 + 2.624 = 9.824
        assert ev == pytest.approx(9.824)
        # Higher than old formula: 0.9 * 10 = 9.0 (because hero profits from calling)
        assert ev > 0.9 * 10.0

    def test_weak_hand_folds_to_villain_bet(self):
        """Weak hand (low equity vs betting range) folds when villain bets."""
        ev = compute_check_ev(
            pot_bb=10.0,
            check_back_pct=0.8,
            villain_bet_pct=0.2,
            eq_vs_checking=0.4,
            eq_vs_betting=0.15,
            v_bet_bb=6.6,
        )
        # check_back: 0.8 * 0.4 * 10 = 3.2
        # call_ev: 0.15 * 23.2 - 6.6 = 3.48 - 6.6 = -3.12
        # facing_bet: max(0, -3.12) = 0 (hero folds)
        # total: 3.2 + 0 = 3.2
        assert ev == pytest.approx(3.2)
        # Lower than old formula: 0.4 * 10 = 4.0 (because hero sometimes faces a bet and folds)

    def test_medium_hand_marginal_call(self):
        """Hand that barely breaks even calling villain's bet."""
        # Call EV = eq * (pot + 2*v_bet) - v_bet
        # Break even: eq * (10 + 13.2) - 6.6 = 0 → eq = 6.6/23.2 ≈ 0.2845
        ev_fold = compute_check_ev(
            pot_bb=10.0, check_back_pct=0.8, villain_bet_pct=0.2,
            eq_vs_checking=0.5, eq_vs_betting=0.28,  # just below break-even
            v_bet_bb=6.6,
        )
        ev_call = compute_check_ev(
            pot_bb=10.0, check_back_pct=0.8, villain_bet_pct=0.2,
            eq_vs_checking=0.5, eq_vs_betting=0.30,  # just above break-even
            v_bet_bb=6.6,
        )
        # Both should have same check-back component (0.8 * 0.5 * 10 = 4.0)
        # But the one above break-even should have slightly higher EV
        assert ev_call > ev_fold

    def test_villain_always_bets_hero_always_folds(self):
        """If villain always bets and hero can't call, EV = 0."""
        ev = compute_check_ev(
            pot_bb=10.0,
            check_back_pct=0.0,
            villain_bet_pct=1.0,
            eq_vs_checking=0.5,
            eq_vs_betting=0.0,
            v_bet_bb=6.6,
        )
        assert ev == pytest.approx(0.0)

    def test_zero_pot(self):
        ev = compute_check_ev(
            pot_bb=0.0, check_back_pct=0.5, villain_bet_pct=0.5,
            eq_vs_checking=0.5, eq_vs_betting=0.5, v_bet_bb=0.0,
        )
        assert ev == pytest.approx(0.0)


class TestComputeAggressiveEv:
    """Test the Bet/Raise EV formula with raise branch lookahead."""

    def test_villain_always_folds(self):
        """If villain always folds, EV = pot."""
        ev = compute_aggressive_ev(
            pot_bb=10.0, bet_bb=3.3,
            fold_pct=1.0, call_pct=0.0, raise_pct=0.0,
            eq_vs_callers=0.5, eq_vs_raising=0.5, v_raise_bb=9.9,
        )
        assert ev == pytest.approx(10.0)

    def test_villain_always_calls(self):
        """If villain always calls, EV = eq*(pot+2*bet) - bet."""
        ev = compute_aggressive_ev(
            pot_bb=10.0, bet_bb=3.3,
            fold_pct=0.0, call_pct=1.0, raise_pct=0.0,
            eq_vs_callers=0.7, eq_vs_raising=0.5, v_raise_bb=9.9,
        )
        expected = 0.7 * (10.0 + 6.6) - 3.3
        assert ev == pytest.approx(expected)

    def test_raise_branch_strong_hand_calls(self):
        """Strong hand should call the raise, not fold."""
        ev = compute_aggressive_ev(
            pot_bb=10.0, bet_bb=3.3,
            fold_pct=0.0, call_pct=0.0, raise_pct=1.0,
            eq_vs_callers=0.5, eq_vs_raising=0.9,
            v_raise_bb=9.9,
        )
        # hero_call = 9.9 - 3.3 = 6.6
        # call_raise_ev = 0.9 * (10 + 3.3 + 9.9 + 6.6) - (3.3 + 6.6)
        #               = 0.9 * 29.8 - 9.9 = 26.82 - 9.9 = 16.92
        # fold_ev = -3.3
        # raise_branch = max(-3.3, 16.92) = 16.92
        assert ev == pytest.approx(16.92)
        # Old formula would give -3.3 (always fold to raise)
        assert ev > -3.3

    def test_raise_branch_weak_hand_folds(self):
        """Weak hand should fold to raise (raise_ev = -bet)."""
        ev = compute_aggressive_ev(
            pot_bb=10.0, bet_bb=3.3,
            fold_pct=0.0, call_pct=0.0, raise_pct=1.0,
            eq_vs_callers=0.5, eq_vs_raising=0.1,
            v_raise_bb=9.9,
        )
        # hero_call = 6.6
        # call_raise_ev = 0.1 * 29.8 - 9.9 = 2.98 - 9.9 = -6.92
        # fold_ev = -3.3
        # raise_branch = max(-3.3, -6.92) = -3.3 (folds)
        assert ev == pytest.approx(-3.3)

    def test_mixed_villain_response(self):
        """Realistic mix: villain folds 40%, calls 50%, raises 10%."""
        ev = compute_aggressive_ev(
            pot_bb=10.0, bet_bb=3.3,
            fold_pct=0.4, call_pct=0.5, raise_pct=0.1,
            eq_vs_callers=0.6, eq_vs_raising=0.3,
            v_raise_bb=9.9,
        )
        # fold component: 0.4 * 10 = 4.0
        # call component: 0.5 * (0.6 * 16.6 - 3.3) = 0.5 * (9.96 - 3.3) = 0.5 * 6.66 = 3.33
        # raise: hero_call=6.6, call_ev=0.3*29.8-9.9=8.94-9.9=-0.96, fold_ev=-3.3
        #   raise_branch = max(-3.3, -0.96) = -0.96
        # raise component: 0.1 * (-0.96) = -0.096
        # total: 4.0 + 3.33 - 0.096 = 7.234
        assert ev == pytest.approx(7.234)

    def test_old_formula_comparison_weak_hand(self):
        """For weak hands, new formula should be >= old formula (raise branch)."""
        # Old: fold% * pot + call% * (eq*(pot+2bet)-bet) + raise% * (-bet)
        # New: same but raise% * max(-bet, call_raise_ev)
        # Since max(-bet, x) >= -bet, new EV >= old EV for any hand
        for eq_raising in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            new_ev = compute_aggressive_ev(
                pot_bb=10.0, bet_bb=3.3,
                fold_pct=0.4, call_pct=0.5, raise_pct=0.1,
                eq_vs_callers=0.5, eq_vs_raising=eq_raising,
                v_raise_bb=9.9,
            )
            old_ev = (
                0.4 * 10.0
                + 0.5 * (0.5 * 16.6 - 3.3)
                + 0.1 * (-3.3)
            )
            assert new_ev >= old_ev - 1e-9, (
                f"New EV {new_ev} should be >= old EV {old_ev} "
                f"(eq_vs_raising={eq_raising})"
            )

    def test_zero_raise_pct_matches_old_formula(self):
        """With no raise, new formula exactly matches old formula."""
        ev = compute_aggressive_ev(
            pot_bb=10.0, bet_bb=5.0,
            fold_pct=0.5, call_pct=0.5, raise_pct=0.0,
            eq_vs_callers=0.65, eq_vs_raising=0.5, v_raise_bb=15.0,
        )
        old_ev = 0.5 * 10.0 + 0.5 * (0.65 * 20.0 - 5.0)
        assert ev == pytest.approx(old_ev)
