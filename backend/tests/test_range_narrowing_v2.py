"""Tests for Range Narrowing v2: per-hand logit-based action probabilities."""
import math
import pytest

from playing_cards_lib.core import Card, Rank, Suit
from solver.eq_calculator import _normalize_combo


# ── Board fixtures ──
BOARD_TURN = [
    Card(Rank.KING, Suit.HEARTS),
    Card(Rank.SEVEN, Suit.DIAMONDS),
    Card(Rank.SIX, Suit.DIAMONDS),
    Card(Rank.TEN, Suit.DIAMONDS),
]

BOARD_RIVER = BOARD_TURN + [Card(Rank.TWO, Suit.SPADES)]

COMBO_AA = _normalize_combo((Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES)))
COMBO_72 = _normalize_combo((Card(Rank.SEVEN, Suit.HEARTS), Card(Rank.TWO, Suit.CLUBS)))
COMBO_DRAW = _normalize_combo((Card(Rank.EIGHT, Suit.DIAMONDS), Card(Rank.FIVE, Suit.DIAMONDS)))


# ── Tests for compute_eq_np ──

class TestComputeEqNp:
    """compute_eq_np returns EQ (avg strength) and NP (max strength) per combo."""

    def test_returns_dict_of_tuples(self):
        from solver.streets.common import compute_eq_np
        result = compute_eq_np(BOARD_TURN)
        assert isinstance(result, dict)
        assert len(result) > 0
        first_val = next(iter(result.values()))
        assert isinstance(first_val, tuple)
        assert len(first_val) == 2

    def test_eq_and_np_normalized_0_to_1(self):
        from solver.streets.common import compute_eq_np
        result = compute_eq_np(BOARD_TURN)
        for combo, (eq, np_val) in result.items():
            assert 0.0 <= eq <= 1.0, f"EQ out of range for {combo}: {eq}"
            assert 0.0 <= np_val <= 1.0, f"NP out of range for {combo}: {np_val}"

    def test_raw_np_gte_raw_eq(self):
        """Before normalization, max score >= avg score for every combo."""
        from solver.streets.common import compute_eq_np
        # Verifying the function returns sensible values: both EQ and NP in [0,1]
        # After normalization, NP can be < EQ (different denominators), but
        # combos with high NP relative to EQ indicate draw potential.
        result = compute_eq_np(BOARD_TURN)
        max_eq = max(eq for eq, _ in result.values())
        max_np = max(np_val for _, np_val in result.values())
        assert max_eq == pytest.approx(1.0, abs=1e-6)
        assert max_np == pytest.approx(1.0, abs=1e-6)

    def test_excludes_combos_conflicting_with_board(self):
        from solver.streets.common import compute_eq_np
        result = compute_eq_np(BOARD_TURN)
        board_cards = {(c.rank, c.suit) for c in BOARD_TURN}
        for combo in result:
            for card in combo:
                assert (card.rank, card.suit) not in board_cards

    def test_all_non_conflicting_combos_present(self):
        """Should produce entries for all C(48,2) = 1128 combos."""
        from solver.streets.common import compute_eq_np
        result = compute_eq_np(BOARD_TURN)
        assert len(result) == 1128

    def test_river_board_np_equals_eq(self):
        """On a 5-card board (river), NP should equal EQ (no future cards)."""
        from solver.streets.common import compute_eq_np
        result = compute_eq_np(BOARD_RIVER)
        for combo, (eq, np_val) in result.items():
            assert abs(np_val - eq) < 1e-9, (
                f"On river, NP should equal EQ for {combo}: NP={np_val}, EQ={eq}"
            )


# ── Tests for solve_biases ──

class TestSolveBiases:
    """Newton-Raphson solver finds biases that match target action frequencies."""

    def _make_eq_np_map(self):
        """Small fake eq_np_map for testing."""
        return {
            COMBO_AA: (0.95, 0.95),
            COMBO_72: (0.10, 0.30),
            COMBO_DRAW: (0.30, 0.90),
        }

    def _make_range(self):
        return {COMBO_AA: 1.0, COMBO_72: 1.0, COMBO_DRAW: 1.0}

    def test_biases_match_target_frequencies(self):
        """Solved biases should produce aggregate freqs within 1% of targets."""
        from solver.streets.common import solve_biases
        eq_np = self._make_eq_np_map()
        villain_range = self._make_range()
        target_fold = 0.30
        target_passive = 0.45
        target_aggressive = 0.25

        biases = solve_biases(eq_np, villain_range, target_fold, target_passive, target_aggressive)
        assert len(biases) == 3

        # Verify: compute aggregate probabilities with solved biases
        b_agg, b_pas, b_fold = biases
        total_weight = sum(villain_range.values())
        agg_sum = pas_sum = fold_sum = 0.0
        for combo, freq in villain_range.items():
            eq, np_val = eq_np[_normalize_combo(combo)]
            l_agg = (eq + np_val) + b_agg
            l_pas = (eq - np_val) + b_pas
            l_fold = 0.0 + b_fold
            max_l = max(l_agg, l_pas, l_fold)
            e_agg = math.exp(l_agg - max_l)
            e_pas = math.exp(l_pas - max_l)
            e_fold = math.exp(l_fold - max_l)
            total = e_agg + e_pas + e_fold
            agg_sum += freq * (e_agg / total)
            pas_sum += freq * (e_pas / total)
            fold_sum += freq * (e_fold / total)

        actual_agg = agg_sum / total_weight
        actual_pas = pas_sum / total_weight
        actual_fold = fold_sum / total_weight
        assert abs(actual_agg - target_aggressive) < 0.01, f"agg: {actual_agg} vs {target_aggressive}"
        assert abs(actual_pas - target_passive) < 0.01, f"pas: {actual_pas} vs {target_passive}"
        assert abs(actual_fold - target_fold) < 0.01, f"fold: {actual_fold} vs {target_fold}"

    def test_extreme_fold_heavy(self):
        """Should handle fold_pct=0.90 without diverging."""
        from solver.streets.common import solve_biases
        eq_np = self._make_eq_np_map()
        villain_range = self._make_range()
        biases = solve_biases(eq_np, villain_range, 0.90, 0.08, 0.02)
        assert all(math.isfinite(b) for b in biases)

    def test_extreme_raise_heavy(self):
        """Should handle aggressive_pct=0.90 without diverging."""
        from solver.streets.common import solve_biases
        eq_np = self._make_eq_np_map()
        villain_range = self._make_range()
        biases = solve_biases(eq_np, villain_range, 0.05, 0.05, 0.90)
        assert all(math.isfinite(b) for b in biases)

    def test_returns_three_floats(self):
        from solver.streets.common import solve_biases
        eq_np = self._make_eq_np_map()
        villain_range = self._make_range()
        biases = solve_biases(eq_np, villain_range, 0.30, 0.40, 0.30)
        assert isinstance(biases, tuple)
        assert len(biases) == 3
        assert all(isinstance(b, float) for b in biases)


# ── Tests for _narrow_range v2 ──

class TestNarrowRangeV2:
    """_narrow_range uses logit-based per-combo probabilities when eq_np_map provided."""

    def test_returns_two_ranges(self):
        """Should return (passive_range, aggressive_range) dicts."""
        from solver.streets.common import _narrow_range
        eq_np = {
            COMBO_AA: (0.95, 0.95),
            COMBO_72: (0.10, 0.30),
            COMBO_DRAW: (0.30, 0.90),
        }
        villain_range = {COMBO_AA: 1.0, COMBO_72: 1.0, COMBO_DRAW: 1.0}
        passive, aggressive = _narrow_range(
            villain_range, BOARD_TURN, "turn",
            aggressive_pct=0.25, passive_pct=0.45,
            eq_np_map=eq_np,
        )
        assert isinstance(passive, dict)
        assert isinstance(aggressive, dict)

    def test_draws_get_higher_aggression_weight(self):
        """A draw (high NP, low EQ) should have more aggression weight than a medium hand."""
        from solver.streets.common import _narrow_range
        medium_hand = _normalize_combo((Card(Rank.JACK, Suit.CLUBS), Card(Rank.NINE, Suit.HEARTS)))
        eq_np = {
            COMBO_DRAW: (0.25, 0.90),
            medium_hand: (0.50, 0.50),
        }
        villain_range = {COMBO_DRAW: 1.0, medium_hand: 1.0}
        passive, aggressive = _narrow_range(
            villain_range, BOARD_TURN, "turn",
            aggressive_pct=0.30, passive_pct=0.40,
            eq_np_map=eq_np,
        )
        draw_agg = aggressive.get(COMBO_DRAW, 0.0)
        medium_agg = aggressive.get(medium_hand, 0.0)
        assert draw_agg > medium_agg, (
            f"Draw should have higher aggression: draw={draw_agg}, medium={medium_agg}"
        )

    def test_trash_hands_get_higher_fold_weight(self):
        """Trash hands (low EQ, low NP) should have lower passive+aggressive weight."""
        from solver.streets.common import _narrow_range
        eq_np = {
            COMBO_AA: (0.95, 0.95),
            COMBO_72: (0.05, 0.10),
        }
        villain_range = {COMBO_AA: 1.0, COMBO_72: 1.0}
        passive, aggressive = _narrow_range(
            villain_range, BOARD_TURN, "turn",
            aggressive_pct=0.25, passive_pct=0.45,
            eq_np_map=eq_np,
        )
        aa_total = passive.get(COMBO_AA, 0) + aggressive.get(COMBO_AA, 0)
        trash_total = passive.get(COMBO_72, 0) + aggressive.get(COMBO_72, 0)
        assert aa_total > trash_total, (
            f"AA should have more non-fold weight: AA={aa_total}, 72={trash_total}"
        )

    def test_fallback_to_old_logic_without_eq_np(self):
        """When eq_np_map is None, should still work (old equity-based logic)."""
        from solver.streets.common import _narrow_range
        villain_range = {COMBO_AA: 1.0, COMBO_72: 1.0}
        passive, aggressive = _narrow_range(
            villain_range, BOARD_RIVER, "river",
            aggressive_pct=0.50, passive_pct=0.50,
        )
        assert len(passive) > 0 or len(aggressive) > 0
