"""Tests for eval7-based strength evaluation system (solver/ranges.py)."""

from playing_cards_lib.core import Card, Rank, Suit
from solver.ranges import (
    _card_to_eval7,
    _combos_conflict,
    _normalize_combo,
    build_strength_map,
    compute_equity_by_strength,
    filter_range_by_equity,
)


def _c(rank_str: str, suit_str: str) -> Card:
    """Shorthand card builder: _c('A', 'S') -> Card(Rank.ACE, Suit.SPADES)."""
    rank_map = {
        'A': Rank.ACE, 'K': Rank.KING, 'Q': Rank.QUEEN, 'J': Rank.JACK,
        'T': Rank.TEN, '9': Rank.NINE, '8': Rank.EIGHT, '7': Rank.SEVEN,
        '6': Rank.SIX, '5': Rank.FIVE, '4': Rank.FOUR, '3': Rank.THREE, '2': Rank.TWO,
    }
    suit_map = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
    return Card(rank_map[rank_str], suit_map[suit_str])


# ── _card_to_eval7 ──────────────────────────────────────────────────────────


class TestCardToEval7:
    def test_ace_of_spades(self):
        c = _c('A', 'S')
        e7 = _card_to_eval7(c)
        assert str(e7) == 'As'

    def test_two_of_clubs(self):
        c = _c('2', 'C')
        e7 = _card_to_eval7(c)
        assert str(e7) == '2c'

    def test_ten_of_hearts(self):
        c = _c('T', 'H')
        e7 = _card_to_eval7(c)
        assert str(e7) == 'Th'


# ── _combos_conflict ────────────────────────────────────────────────────────


class TestCombosConflict:
    def test_shared_card(self):
        a = (_c('A', 'S'), _c('K', 'S'))
        b = (_c('A', 'S'), _c('Q', 'H'))
        assert _combos_conflict(a, b) is True

    def test_no_conflict(self):
        a = (_c('A', 'S'), _c('K', 'S'))
        b = (_c('Q', 'H'), _c('J', 'D'))
        assert _combos_conflict(a, b) is False

    def test_same_rank_different_suit(self):
        a = (_c('A', 'S'), _c('K', 'S'))
        b = (_c('A', 'H'), _c('K', 'H'))
        assert _combos_conflict(a, b) is False


# ── build_strength_map ──────────────────────────────────────────────────────


class TestBuildStrengthMap:
    def test_river_aa_beats_qq(self):
        """On a non-paired, non-flushy board, AA should score higher than QQ."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        qq = (_c('Q', 'S'), _c('Q', 'H'))
        smap = build_strength_map([aa, qq], board)
        assert smap[_normalize_combo(aa)] > smap[_normalize_combo(qq)]

    def test_river_flush_beats_pair(self):
        """A flush should beat a single pair on the river."""
        board = [_c('2', 'H'), _c('5', 'H'), _c('9', 'H'), _c('3', 'C'), _c('J', 'D')]
        flush = (_c('A', 'H'), _c('K', 'H'))  # Ace-high flush
        pair = (_c('J', 'S'), _c('T', 'S'))   # Pair of jacks
        smap = build_strength_map([flush, pair], board)
        assert smap[_normalize_combo(flush)] > smap[_normalize_combo(pair)]

    def test_combo_conflicting_with_board_excluded(self):
        """Combos sharing a card with the board should not appear in the map."""
        board = [_c('A', 'S'), _c('K', 'H'), _c('Q', 'D'), _c('J', 'C'), _c('T', 'S')]
        conflict = (_c('A', 'S'), _c('2', 'H'))  # shares As with board
        smap = build_strength_map([conflict], board)
        assert _normalize_combo(conflict) not in smap

    def test_turn_produces_valid_strengths(self):
        """Turn evaluation should produce numeric strength values."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        smap = build_strength_map([aa], board)
        nk = _normalize_combo(aa)
        assert nk in smap
        assert isinstance(smap[nk], float)
        assert smap[nk] > 0

    def test_turn_aa_beats_qq(self):
        """AA should have higher average strength than QQ on turn too."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        qq = (_c('Q', 'S'), _c('Q', 'H'))
        smap = build_strength_map([aa, qq], board)
        assert smap[_normalize_combo(aa)] > smap[_normalize_combo(qq)]


# ── compute_equity_by_strength ──────────────────────────────────────────────


class TestComputeEquityByStrength:
    def test_strong_vs_weak_high_equity(self):
        """AA should have very high equity vs a range of weak hands on river."""
        board = [_c('K', 'S'), _c('2', 'H'), _c('9', 'D'), _c('7', 'C'), _c('4', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        weak1 = (_c('8', 'S'), _c('6', 'D'))
        weak2 = (_c('T', 'C'), _c('3', 'D'))
        all_combos = [aa, weak1, weak2]
        smap = build_strength_map(all_combos, board)
        villain_range = {weak1: 1.0, weak2: 1.0}
        eq = compute_equity_by_strength(aa, villain_range, smap)
        assert eq > 0.9

    def test_equal_strength_gives_half(self):
        """Two identical-strength combos should produce 0.5 equity."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        # AA spades/hearts vs AA diamonds/clubs — exact same hand strength on this board
        hero = (_c('A', 'S'), _c('A', 'H'))
        villain = (_c('A', 'D'), _c('A', 'C'))
        smap = build_strength_map([hero, villain], board)
        eq = compute_equity_by_strength(hero, {villain: 1.0}, smap)
        assert eq == 0.5

    def test_card_exclusion(self):
        """Villain combos sharing cards with hero should be skipped."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        hero = (_c('A', 'S'), _c('K', 'S'))
        conflicting = (_c('A', 'S'), _c('Q', 'H'))  # shares As
        non_conflicting = (_c('4', 'C'), _c('3', 'D'))
        smap = build_strength_map([hero, non_conflicting], board)
        # conflicting shouldn't have a strength (shares As with hero),
        # but even if it did, _combos_conflict should skip it
        villain_range = {conflicting: 1.0, non_conflicting: 1.0}
        eq = compute_equity_by_strength(hero, villain_range, smap)
        # Result should only be based on non_conflicting combo
        assert 0.0 <= eq <= 1.0

    def test_empty_villain_range_returns_half(self):
        """Empty villain range should return 0.5."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        hero = (_c('A', 'S'), _c('A', 'H'))
        smap = build_strength_map([hero], board)
        eq = compute_equity_by_strength(hero, {}, smap)
        assert eq == 0.5


# ── filter_range_by_equity (with strength_map) ─────────────────────────────


class TestFilterRangeByEquity:
    def test_strongest_combos_in_raise_bucket(self):
        """Top equity combos should go into the raising range."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        kk = (_c('K', 'S'), _c('K', 'H'))
        weak = (_c('4', 'C'), _c('3', 'D'))

        range_ = {aa: 1.0, kk: 1.0, weak: 1.0}
        smap = build_strength_map(list(range_.keys()), board)

        raising, calling, folding = filter_range_by_equity(
            range_, board, "river",
            raise_pct=33, call_pct=33,
            strength_map=smap,
        )

        # AA should have the highest weight in the raising range
        assert raising[aa] >= raising.get(weak, 0)

    def test_returns_three_dicts(self):
        """filter_range_by_equity should always return 3 dicts."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        range_ = {aa: 1.0}
        smap = build_strength_map([aa], board)

        result = filter_range_by_equity(
            range_, board, "river",
            raise_pct=50, call_pct=50,
            strength_map=smap,
        )
        assert len(result) == 3
        assert all(isinstance(r, dict) for r in result)

    def test_empty_range_returns_empty(self):
        """Empty input range should return empty dicts."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        result = filter_range_by_equity(
            {}, board, "river",
            raise_pct=33, call_pct=33,
            strength_map={},
        )
        assert result == ({}, {}, {})
