import pytest
from app.parsers.equity import (
    get_equity, EQUITY_GRID, VALID_TRIPLES, MADE_HAND_RANK,
    made_vs_made, is_impossible_triple, HandTriple,
)
from app.models.enums import MadeHandType, FlushDrawType, StraightDrawType


M = MadeHandType
F = FlushDrawType
S = StraightDrawType


class TestMadeHandRank:

    def test_no_made_hand_is_zero(self):
        assert MADE_HAND_RANK[M.NO_MADE_HAND] == 0

    def test_ace_high_beats_no_made_hand(self):
        assert MADE_HAND_RANK[M.ACE_HIGH] > MADE_HAND_RANK[M.NO_MADE_HAND]

    def test_all_ranks_unique(self):
        values = list(MADE_HAND_RANK.values())
        assert len(values) == len(set(values))


class TestMadeVsMade:

    def test_higher_rank_wins(self):
        assert made_vs_made(M.SET, M.PAIR) == pytest.approx(0.92)

    def test_lower_rank_loses(self):
        assert made_vs_made(M.PAIR, M.SET) == pytest.approx(0.08)

    def test_same_rank_splits(self):
        assert made_vs_made(M.TOP_PAIR, M.TOP_PAIR) == pytest.approx(0.50)


class TestImpossibleTriples:

    def test_flush_with_flush_draw(self):
        assert is_impossible_triple(M.FLUSH, F.FRONT_DOOR, S.NONE)

    def test_straight_with_oesd(self):
        assert is_impossible_triple(M.STRAIGHT, F.NONE, S.OESD)

    def test_quads_with_any_draw(self):
        assert is_impossible_triple(M.QUADS, F.FRONT_DOOR, S.NONE)

    def test_top_pair_no_draws_is_valid(self):
        assert not is_impossible_triple(M.TOP_PAIR, F.NONE, S.NONE)

    def test_combo_draw_is_valid(self):
        assert not is_impossible_triple(M.NO_MADE_HAND, F.FRONT_DOOR, S.OESD)


class TestValidTriples:

    def test_no_impossible_triples_in_list(self):
        for made, fd, sd in VALID_TRIPLES:
            assert not is_impossible_triple(made, fd, sd)

    def test_count_is_reasonable(self):
        assert 60 < len(VALID_TRIPLES) < 90


class TestEquityGrid:

    def test_all_three_streets_present(self):
        assert set(EQUITY_GRID.keys()) == {"flop", "turn", "river"}

    def test_grid_size_matches_valid_triples(self):
        expected = len(VALID_TRIPLES) ** 2
        for street in ("flop", "turn", "river"):
            assert len(EQUITY_GRID[street]) == expected

    def test_all_equities_between_zero_and_one(self):
        for street_grid in EQUITY_GRID.values():
            for eq in street_grid.values():
                assert 0.0 <= eq <= 1.0

    def test_mirror_equities_sum_to_one(self):
        grid = EQUITY_GRID["flop"]
        for hero in VALID_TRIPLES[:10]:
            for villain in VALID_TRIPLES[:10]:
                assert grid[(hero, villain)] + grid[(villain, hero)] == pytest.approx(1.0, abs=0.01)


class TestGetEquity:

    def test_top_pair_vs_pair_plus_fd_on_flop(self):
        eq = get_equity((M.TOP_PAIR, F.NONE, S.NONE), (M.PAIR, F.FRONT_DOOR, S.NONE), "flop")
        assert 0.55 < eq < 0.75

    def test_combo_draw_vs_overpair_on_flop(self):
        eq = get_equity((M.NO_MADE_HAND, F.FRONT_DOOR, S.OESD), (M.OVERPAIR, F.NONE, S.NONE), "flop")
        assert 0.45 < eq < 0.60

    def test_flush_vs_pair_on_river(self):
        eq = get_equity((M.FLUSH, F.NONE, S.NONE), (M.PAIR, F.NONE, S.NONE), "river")
        assert eq == pytest.approx(0.92)

    def test_same_hand_is_fifty_fifty(self):
        eq = get_equity((M.TOP_PAIR, F.NONE, S.NONE), (M.TOP_PAIR, F.NONE, S.NONE), "flop")
        assert eq == pytest.approx(0.50, abs=0.01)
        
    def test_turn_villain_has_fewer_outs(self):
        eq_flop = get_equity((M.TOP_PAIR, F.NONE, S.NONE), (M.PAIR, F.FRONT_DOOR, S.NONE), "flop")
        eq_turn = get_equity((M.TOP_PAIR, F.NONE, S.NONE), (M.PAIR, F.FRONT_DOOR, S.NONE), "turn")
        assert eq_turn > eq_flop
