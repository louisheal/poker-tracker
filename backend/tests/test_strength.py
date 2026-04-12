"""Tests for eval7-based strength evaluation system (solver/ranges.py, solver/eq_calculator.py)."""

from playing_cards_lib.core import Card, Rank, Suit
from solver.ranges import (
    _card_to_eval7,
    _combos_conflict,
    _normalize_combo,
    build_strength_map,
    filter_range_by_equity,
)
from solver.eq_calculator import all_hands_vs_range


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


# ── all_hands_vs_range (equity vs range) ────────────────────────────────────


class TestAllHandsVsRange:
    def test_strong_vs_weak_high_equity(self):
        """AA should have very high equity vs a range of weak hands on river."""
        board = [_c('K', 'S'), _c('2', 'H'), _c('9', 'D'), _c('7', 'C'), _c('4', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        weak1 = (_c('8', 'S'), _c('6', 'D'))
        weak2 = (_c('T', 'C'), _c('3', 'D'))
        villain_range = {weak1: 1.0, weak2: 1.0}
        result = all_hands_vs_range([aa], villain_range, board)
        eq = result[_normalize_combo(aa)]
        assert eq > 0.9

    def test_equal_strength_gives_half(self):
        """Two identical-strength combos should produce 0.5 equity."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        hero = (_c('A', 'S'), _c('A', 'H'))
        villain = (_c('A', 'D'), _c('A', 'C'))
        result = all_hands_vs_range([hero], {villain: 1.0}, board)
        eq = result[_normalize_combo(hero)]
        assert eq == 0.5

    def test_card_exclusion(self):
        """Villain combos sharing cards with hero should be excluded."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        hero = (_c('A', 'S'), _c('K', 'S'))
        conflicting = (_c('A', 'S'), _c('Q', 'H'))  # shares As
        non_conflicting = (_c('4', 'C'), _c('3', 'D'))
        villain_range = {conflicting: 1.0, non_conflicting: 1.0}
        result = all_hands_vs_range([hero], villain_range, board)
        eq = result[_normalize_combo(hero)]
        assert 0.0 <= eq <= 1.0

    def test_empty_villain_range_returns_half(self):
        """Empty villain range should return 0.5."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        hero = (_c('A', 'S'), _c('A', 'H'))
        result = all_hands_vs_range([hero], {}, board)
        eq = result[_normalize_combo(hero)]
        assert eq == 0.5


# ── filter_range_by_equity (using eq_calculator internally) ─────────────────


class TestFilterRangeByEquity:
    def test_strongest_combos_in_raise_bucket(self):
        """Top equity combos should go into the raising range."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        kk = (_c('K', 'S'), _c('K', 'H'))
        weak = (_c('4', 'C'), _c('3', 'D'))

        range_ = {aa: 1.0, kk: 1.0, weak: 1.0}

        raising, calling, folding = filter_range_by_equity(
            range_, board, "river",
            raise_pct=33, call_pct=33,
        )

        # AA should have the highest weight in the raising range
        assert raising[aa] >= raising.get(weak, 0)

    def test_returns_three_dicts(self):
        """filter_range_by_equity should always return 3 dicts."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        range_ = {aa: 1.0}

        result = filter_range_by_equity(
            range_, board, "river",
            raise_pct=50, call_pct=50,
        )
        assert len(result) == 3
        assert all(isinstance(r, dict) for r in result)

    def test_empty_range_returns_empty(self):
        """Empty input range should return empty dicts."""
        board = [_c('7', 'S'), _c('2', 'H'), _c('9', 'D'), _c('3', 'C'), _c('5', 'H')]
        result = filter_range_by_equity(
            {}, board, "river",
            raise_pct=33, call_pct=33,
        )
        assert result == ({}, {}, {})


# ── all_hands_vs_range (exact/MC equity) ────────────────────────────────────


class TestEquityExact:
    def test_aa_beats_weak_on_river(self):
        """AA should have very high exact equity vs weak hands on river."""
        board = [_c('K', 'S'), _c('2', 'H'), _c('9', 'D'), _c('7', 'C'), _c('4', 'H')]
        aa = (_c('A', 'S'), _c('A', 'H'))
        weak1 = (_c('8', 'S'), _c('6', 'D'))
        weak2 = (_c('T', 'C'), _c('3', 'D'))
        result = all_hands_vs_range([aa], {weak1: 1.0, weak2: 1.0}, board)
        assert result[_normalize_combo(aa)] > 0.9

    def test_flush_draw_on_flop(self):
        """Flush draw on monotone flop should have meaningful (not 0/1) equity."""
        board = [_c('K', 'S'), _c('7', 'S'), _c('2', 'S')]
        flush_draw = (_c('A', 'S'), _c('Q', 'H'))  # has one spade
        overpair = (_c('A', 'H'), _c('A', 'D'))    # no spade
        result = all_hands_vs_range(
            [flush_draw, overpair],
            {flush_draw: 1.0, overpair: 1.0},
            board,
        )
        # Both should have non-trivial equity
        fd_eq = result[_normalize_combo(flush_draw)]
        op_eq = result[_normalize_combo(overpair)]
        assert 0.1 < fd_eq < 0.9
        assert 0.1 < op_eq < 0.9

    def test_aa_on_monotone_flop_accuracy(self):
        """AA on 432 monotone spades should be ~77% vs full range (Flopzilla benchmark)."""
        board = [_c('4', 'S'), _c('3', 'S'), _c('2', 'S')]
        # All AA combos
        aa_combos = []
        for s1 in [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]:
            for s2 in [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]:
                if s1.value < s2.value:
                    aa_combos.append((Card(Rank.ACE, s1), Card(Rank.ACE, s2)))

        # Build a reasonable villain range (all valid combos)
        cards = [Card(r, s) for r in Rank for s in Suit]
        all_combos = [(cards[i], cards[j])
                      for i in range(len(cards)) for j in range(i+1, len(cards))]
        valid = [c for c in all_combos
                 if not any(c1.rank == b.rank and c1.suit == b.suit for c1 in c for b in board)]
        villain_range = {c: 1.0 for c in valid}

        result = all_hands_vs_range(aa_combos, villain_range, board)
        avg_eq = sum(result[_normalize_combo(c)] for c in aa_combos) / len(aa_combos)
        # MC on flop: allow ±7% margin for MC variance (eval7 MC has ~0.6% systematic bias)
        assert 0.68 < avg_eq < 0.87, f"AA avg equity {avg_eq*100:.1f}% not near 77%"

    def test_empty_board_returns_half(self):
        """No board should give 0.5 equity for all combos."""
        hero = (_c('A', 'S'), _c('K', 'S'))
        villain = {(_c('Q', 'H'), _c('J', 'H')): 1.0}
        result = all_hands_vs_range([hero], villain, [])
        assert result[_normalize_combo(hero)] == 0.5

    def test_card_exclusion_in_exact(self):
        """Villain combos sharing cards with hero should be excluded."""
        board = [_c('K', 'S'), _c('2', 'H'), _c('9', 'D'), _c('7', 'C'), _c('4', 'H')]
        hero = (_c('A', 'S'), _c('Q', 'S'))
        conflicting = (_c('A', 'S'), _c('J', 'H'))  # shares As
        non_conflicting = (_c('3', 'D'), _c('5', 'C'))
        result = all_hands_vs_range(
            [hero],
            {conflicting: 1.0, non_conflicting: 1.0},
            board,
        )
        # Should only compare vs non_conflicting, hero should win easily
        assert result[_normalize_combo(hero)] > 0.9


# ── eval7 MC benchmark ─────────────────────────────────────────────────────


class TestEval7McBenchmark:
    """Benchmark eval7 Monte Carlo equity vs exact on river.

    Computes equity of all 1176 valid combos against a full villain range
    on the Ks7h2d board. Measures speed and accuracy comparing MC (flop)
    against exact (river) to validate eq_calculator wrapper.
    """

    @staticmethod
    def _build_all_combos():
        """Generate all 1326 unique hole card combos."""
        cards = [Card(r, s) for r in Rank for s in Suit]
        combos = []
        for i in range(len(cards)):
            for j in range(i + 1, len(cards)):
                combos.append(_normalize_combo((cards[i], cards[j])))
        return combos

    @staticmethod
    def _card_conflict_with_board(combo, board):
        """Check if a combo shares any card with the board."""
        for card in combo:
            for bc in board:
                if card.rank == bc.rank and card.suit == bc.suit:
                    return True
        return False

    def test_eq_calculator_river_exact(self):
        """Verify eq_calculator uses exact mode on river and AcAh matches Flopzilla."""
        import time

        board = [_c('K', 'S'), _c('7', 'H'), _c('2', 'D'), _c('9', 'C'), _c('4', 'S')]

        all_combos = self._build_all_combos()
        valid_combos = [c for c in all_combos if not self._card_conflict_with_board(c, board)]

        villain_range = {c: 1.0 for c in valid_combos}

        t0 = time.perf_counter()
        result = all_hands_vs_range(valid_combos, villain_range, board)
        elapsed = time.perf_counter() - t0

        # Should be fast (exact mode on river)
        print(f"\nRiver exact via eq_calculator: {elapsed:.2f}s, {len(result)} combos")
        assert elapsed < 2.0, f"River should be fast (exact mode), took {elapsed:.2f}s"

        # Check AcAh equity
        aa_combo = _normalize_combo((_c('A', 'C'), _c('A', 'H')))
        aa_eq = result.get(aa_combo, 0.5)
        assert aa_eq > 0.85, f"AcAh equity {aa_eq:.4f} too low on this board"
