"""Tests for the recursive turn solver (streets/turn.py)."""

import pytest
from unittest.mock import patch, MagicMock

from playing_cards_lib.core import Card, Rank, Suit

from solver.streets.common import _enumerate_sequences


RANK_MAP = {
    "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
    "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
    "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE,
}
SUIT_MAP = {"h": Suit.HEARTS, "d": Suit.DIAMONDS, "s": Suit.SPADES, "c": Suit.CLUBS}


def _c(s: str) -> Card:
    return Card(RANK_MAP[s[0]], SUIT_MAP[s[1]])


BOARD_TURN = [_c("Kh"), _c("7d"), _c("6d"), _c("Td")]

HERO_AK = (_c("Ac"), _c("Kd"))
HERO_QJ = (_c("Qs"), _c("Jc"))

VILLAIN_RANGE = {
    (_c("Qh"), _c("Jh")): 1.0,
    (_c("9s"), _c("8s")): 1.0,
    (_c("5h"), _c("4h")): 1.0,
}


def _build_cache(pot, facing_bet, remaining_bb, is_opener, overrides=None):
    """Build a prediction cache with real keys from _enumerate_sequences,
    filled with default villain responses. Override specific keys as needed.

    Default: villain folds to aggression, checks back when not facing.
    All-in nodes: 50/50 fold/call.
    """
    sequences = _enumerate_sequences(
        pot, facing_bet, remaining_bb,
        cache_key_prefix="", is_opener=is_opener, tokens_so_far=[],
    )
    cache = {}
    for cache_key, is_facing, is_all_in, _ in sequences:
        if is_all_in:
            cache[cache_key] = (0.5, 0.5, 0.0)
        elif is_facing:
            cache[cache_key] = (1.0, 0.0, 0.0)
        else:
            cache[cache_key] = (0.0, 1.0, 0.0)

    if overrides:
        cache.update(overrides)
    return cache


def _constant_river_mock(ev_per_combo):
    """Create a solve_river mock that returns a fixed EV for every combo and card."""
    def fake_river(**kwargs):
        combos = kwargs["hero_combos"]
        action_evs = {"Check": {c: ev_per_combo for c in combos}}
        return action_evs, {c: 0.5 for c in combos}
    return fake_river


def _river_mock_best_is_pot():
    """solve_river where hero's best action = pot (villain folds to any bet)."""
    def fake_river(**kwargs):
        combos = kwargs["hero_combos"]
        pot = kwargs["pot"]
        action_evs = {
            "Check": {c: 0.0 for c in combos},
            "B33": {c: pot for c in combos},
        }
        return action_evs, {c: 0.0 for c in combos}
    return fake_river


class TestSolveRiverForAllCards:
    """Unit tests for _solve_river_for_all_cards: river card enumeration and averaging."""

    @patch("solver.streets.turn.solve_river")
    def test_averages_river_evs_uniformly(self, mock_solve_river):
        """Each river card contributes equally. Constant EV → average = that EV."""
        from solver.streets.turn import _solve_river_for_all_cards

        mock_solve_river.side_effect = _constant_river_mock(15.0)

        result = _solve_river_for_all_cards(
            board=BOARD_TURN, pot=10.0, remaining_bb=90.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        assert abs(result[HERO_AK] - 15.0) < 0.01

    @patch("solver.streets.turn.solve_river")
    def test_excludes_conflicting_combos_per_card(self, mock_solve_river):
        """Combos sharing a card with the river card are excluded from that card's solve."""
        from solver.streets.turn import _solve_river_for_all_cards

        calls = []
        def tracking_river(**kwargs):
            calls.append({"river": kwargs["board"][4], "combos": list(kwargs["hero_combos"])})
            combos = kwargs["hero_combos"]
            return {"Check": {c: 10.0 for c in combos}}, {}

        mock_solve_river.side_effect = tracking_river

        _solve_river_for_all_cards(
            board=BOARD_TURN, pot=10.0, remaining_bb=90.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        for entry in calls:
            if entry["river"] == _c("Ac") or entry["river"] == _c("Kd"):
                assert HERO_AK not in entry["combos"], (
                    f"HERO_AK should be excluded when river={entry['river']}"
                )

    @patch("solver.streets.turn.solve_river")
    def test_passes_correct_pot_and_remaining(self, mock_solve_river):
        """Pot and remaining_bb passed to solve_river match what was given."""
        from solver.streets.turn import _solve_river_for_all_cards

        seen = []
        def tracking_river(**kwargs):
            seen.append({"pot": kwargs["pot"], "remaining": kwargs["remaining_bb"]})
            combos = kwargs["hero_combos"]
            return {"Check": {c: 10.0 for c in combos}}, {}

        mock_solve_river.side_effect = tracking_river

        _solve_river_for_all_cards(
            board=BOARD_TURN, pot=42.0, remaining_bb=79.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_QJ],
            starting_bb=100.0, hero_is_ip=True,
        )
        assert all(s["pot"] == 42.0 for s in seen)
        assert all(s["remaining"] == 79.0 for s in seen)

    @patch("solver.streets.turn.solve_river")
    def test_varying_evs_across_river_cards(self, mock_solve_river):
        """Different river cards produce different EVs; average reflects the mix."""
        from solver.streets.turn import _solve_river_for_all_cards

        def suit_dependent_river(**kwargs):
            combos = kwargs["hero_combos"]
            river_card = kwargs["board"][4]
            ev = 20.0 if river_card.suit == Suit.HEARTS else 10.0
            return {"Check": {c: ev for c in combos}}, {}

        mock_solve_river.side_effect = suit_dependent_river

        result = _solve_river_for_all_cards(
            board=BOARD_TURN, pot=10.0, remaining_bb=90.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_QJ],
            starting_bb=100.0, hero_is_ip=True,
        )
        # 48 remaining cards. HERO_QJ = (Qs, Jc) conflicts with Qs and Jc → 46 valid.
        # Board has Kh → 12 hearts remain in deck. Neither Qs nor Jc is a heart.
        # 12 heart cards × 20 + 34 non-heart cards × 10 = 580 / 46 ≈ 12.61
        expected = (12 * 20.0 + 34 * 10.0) / 46
        assert abs(result[HERO_QJ] - expected) < 0.1


    @patch("solver.streets.turn.solve_river")
    def test_all_in_on_turn_passes_zero_remaining(self, mock_solve_river):
        """When pot + remaining forces remaining_bb=0, solve_river receives 0 remaining."""
        from solver.streets.turn import _solve_river_for_all_cards

        seen = []
        def tracking_river(**kwargs):
            seen.append(kwargs["remaining_bb"])
            combos = kwargs["hero_combos"]
            pot = kwargs["pot"]
            return {"Check": {c: pot for c in combos}}, {c: 1.0 for c in combos}

        mock_solve_river.side_effect = tracking_river

        _solve_river_for_all_cards(
            board=BOARD_TURN, pot=200.0, remaining_bb=0.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_QJ],
            starting_bb=100.0, hero_is_ip=True,
        )
        assert len(seen) > 0, "solve_river should still be called with remaining_bb=0"
        assert all(r == 0.0 for r in seen), "All river calls should get remaining_bb=0"


class TestSolveTurnScenarios:
    """Scenario tests for solve_turn with mocked turn predictions and river outcomes."""

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_fold_ev_is_zero(self, mock_cache, mock_solve_river):
        """Fold always returns EV=0 regardless of other conditions."""
        from solver.streets.turn import solve_turn

        mock_cache.return_value = _build_cache(10, 5, 95, is_opener=False)
        mock_solve_river.side_effect = _constant_river_mock(50.0)

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=5.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        assert result["Fold"][HERO_AK] == 0.0

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_delayed_value_check_to_trap(self, mock_cache, mock_solve_river):
        """Hero OOP with 100% equity: check turn (villain checks back) → extract
        value on river. Better than betting (villain folds immediately)."""
        from solver.streets.turn import solve_turn

        cache = _build_cache(10, 0, 95, is_opener=True, overrides={
            "X": (0.0, 1.0, 0.0),  # villain checks back 100%
        })
        mock_cache.return_value = cache

        # River: hero has 100% equity → wins pot at minimum (check-through showdown)
        mock_solve_river.side_effect = _constant_river_mock(100.0)

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=0.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=False,
        )
        # Check: villain checks back → river avg = 100 → check EV ≈ 100
        # B33: villain folds → EV = pot = 10
        check_ev = result["Check"][HERO_AK]
        bet_evs = [result[a][HERO_AK] for a in result if a not in ("Check", "Fold")]
        assert all(check_ev > bev for bev in bet_evs), (
            f"Check ({check_ev}) should beat all bets ({bet_evs})"
        )

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_max_value_bet_big_when_villain_calls(self, mock_cache, mock_solve_river):
        """Hero IP with 100% equity: villain check-calls any turn bet,
        check-folds any river bet. Largest bet extracts max value."""
        from solver.streets.turn import solve_turn

        cache = _build_cache(10, 0, 95, is_opener=False, overrides={
            # Hero is IP (not opener). All bet entries: villain always calls.
        })
        for key in list(cache):
            if cache[key][2] == 0:
                cache[key] = (0.0, 1.0, 0.0)  # villain calls everything

        mock_cache.return_value = cache

        # River: villain folds to any bet → hero wins pot
        mock_solve_river.side_effect = _river_mock_best_is_pot()

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=0.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        # Larger bets create bigger pots → higher river pot to win
        # B200 (or All-in) should be best or near-best
        action_evs = {a: result[a][HERO_AK] for a in result if a != "Fold"}
        best_action = max(action_evs, key=action_evs.get)
        assert best_action != "Check", (
            f"A bet should be better than Check. EVs: {action_evs}"
        )

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_never_call_all_in_with_zero_equity(self, mock_cache, mock_solve_river):
        """Hero IP, 0% equity, villain shoves. Fold > Call."""
        from solver.streets.turn import solve_turn

        # Villain shoves: facing_bet = remaining_bb = 95 → hero actions: Fold, Call
        cache = _build_cache(10, 95, 95, is_opener=False)
        mock_cache.return_value = cache

        # River: 0% equity, no chips left → EV = 0 everywhere
        mock_solve_river.side_effect = _constant_river_mock(0.0)

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=95.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        fold_ev = result["Fold"][HERO_AK]
        call_ev = result["Call"][HERO_AK]
        assert fold_ev > call_ev, f"Fold ({fold_ev}) should beat Call ({call_ev})"

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_implied_odds_call_to_bluff_river(self, mock_cache, mock_solve_river):
        """Hero IP, 0% equity, facing a turn bet. Villain folds to any river bet.
        Calling the turn to bluff the river is profitable."""
        from solver.streets.turn import solve_turn

        cache = _build_cache(10, 5, 95, is_opener=False, overrides={
            # R3x: villain always raises (makes raising bad)
        })
        for key in list(cache):
            is_facing = not key.startswith("X")
            cache[key] = (0.0, 0.0, 1.0) if is_facing else cache[key]
        # Fix all-in entries: villain can only fold/call
        sequences = _enumerate_sequences(10, 5, 95, "", is_opener=False, tokens_so_far=[])
        for cache_key, _, is_all_in, _ in sequences:
            if is_all_in:
                cache[cache_key] = (1.0, 0.0, 0.0)  # villain folds all-in

        mock_cache.return_value = cache

        # River: villain folds to any bet → hero wins pot
        mock_solve_river.side_effect = _river_mock_best_is_pot()

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=5.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        call_ev = result["Call"][HERO_AK]
        fold_ev = result["Fold"][HERO_AK]
        assert call_ev > fold_ev, f"Call ({call_ev}) should beat Fold ({fold_ev})"

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_no_implied_odds_fold_when_river_bluff_fails(self, mock_cache, mock_solve_river):
        """Hero IP, 0% equity, facing turn bet. Villain calls any river bet (no fold equity).
        Without implied odds, Fold > Call."""
        from solver.streets.turn import solve_turn

        cache = _build_cache(10, 5, 95, is_opener=False)
        mock_cache.return_value = cache

        # River: 0% equity, villain never folds → hero can't win
        mock_solve_river.side_effect = _constant_river_mock(0.0)

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=5.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        fold_ev = result["Fold"][HERO_AK]
        call_ev = result["Call"][HERO_AK]
        assert fold_ev > call_ev, f"Fold ({fold_ev}) should beat Call ({call_ev})"

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_never_fold_100_equity_facing_shove(self, mock_cache, mock_solve_river):
        """Hero IP, 100% equity, villain shoves. Call > Fold."""
        from solver.streets.turn import solve_turn

        cache = _build_cache(10, 95, 95, is_opener=False)
        mock_cache.return_value = cache

        # River with 100% equity: hero wins entire pot
        def full_equity_river(**kwargs):
            combos = kwargs["hero_combos"]
            pot = kwargs["pot"]
            return {"Check": {c: pot for c in combos}}, {c: 1.0 for c in combos}

        mock_solve_river.side_effect = full_equity_river

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=95.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        call_ev = result["Call"][HERO_AK]
        fold_ev = result["Fold"][HERO_AK]
        assert call_ev > fold_ev, f"Call ({call_ev}) should beat Fold ({fold_ev})"

    @patch("solver.streets.turn.solve_river")
    @patch("solver.streets.turn._build_prediction_cache")
    def test_adequate_pot_odds_call_with_equity(self, mock_cache, mock_solve_river):
        """Hero IP, ~30% equity, villain bets 50% pot. Good pot odds → Call EV > 0."""
        from solver.streets.turn import solve_turn

        cache = _build_cache(10, 5, 95, is_opener=False)
        mock_cache.return_value = cache

        # River: hero has ~30% equity at showdown (check-through EV = 0.3 × pot)
        def partial_equity_river(**kwargs):
            combos = kwargs["hero_combos"]
            pot = kwargs["pot"]
            ev = 0.3 * pot
            return {"Check": {c: ev for c in combos}}, {c: 0.3 for c in combos}

        mock_solve_river.side_effect = partial_equity_river

        result, _ = solve_turn(
            board=BOARD_TURN, pot=10.0, facing_bet=5.0, remaining_bb=95.0,
            villain_range=VILLAIN_RANGE, model=MagicMock(),
            action_prefix=[], hero_combos=[HERO_AK],
            starting_bb=100.0, hero_is_ip=True,
        )
        # Call: new_pot=20, river EV = 0.3 × 20 = 6. Call EV = 6 - 5 = 1 > 0.
        call_ev = result["Call"][HERO_AK]
        assert call_ev > 0, f"Call EV ({call_ev}) should be positive with 30% equity"
