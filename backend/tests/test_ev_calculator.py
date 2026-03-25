import pytest
from app.parsers.ev_calculator import calculate_ev_open, calculate_ev_vs_bet
from app.parsers.equity import VALID_TRIPLES, is_impossible_triple
from app.models.enums import MadeHandType as M, FlushDrawType as F, StraightDrawType as S

DEFAULT_EQUITY = 0.5


@pytest.fixture
def make_node_data():
    """Factory for node_data dicts with sensible defaults."""
    def _make(
        fold_count=5, call_count=6, raise_count=2,
        equity_vs_full=None, equity_vs_call=None, equity_vs_raise=None,
        pot_bb=6.5, median_raise_size_pct=250,
    ):
        return {
            "equity_vs_full": equity_vs_full or {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
            "equity_vs_call": equity_vs_call or {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
            "equity_vs_raise": equity_vs_raise or {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
            "fold_count": fold_count,
            "call_count": call_count,
            "raise_count": raise_count,
            "median_raise_size_pct": median_raise_size_pct,
            "pot_bb": pot_bb,
            "street": "flop",
            "hand_count": 120,
            "next_actor": "hero",
        }
    return _make


class TestEvOpen:
    def test_returns_rows_and_actions(self, make_node_data):
        result = calculate_ev_open(make_node_data(), [33, 66])
        assert "rows" in result
        assert result["available_actions"] == ["X", "B33", "B66"]

    def test_row_count_matches_valid_triples(self, make_node_data):
        result = calculate_ev_open(make_node_data(), [33])
        assert len(result["rows"]) == len(VALID_TRIPLES)

    def test_each_row_has_required_fields(self, make_node_data):
        result = calculate_ev_open(make_node_data(), [33])
        for row in result["rows"]:
            assert "made" in row
            assert "flush_draw" in row
            assert "straight_draw" in row
            assert "evs" in row
            assert "best_action" in row
            assert "X" in row["evs"]
            assert "B33" in row["evs"]

    def test_no_impossible_triples_in_output(self, make_node_data):
        result = calculate_ev_open(make_node_data(), [33])
        for row in result["rows"]:
            assert not is_impossible_triple(M(row["made"]), F(row["flush_draw"]), S(row["straight_draw"]))

    def test_higher_equity_gives_higher_check_ev(self, make_node_data):
        eq_full = {t: DEFAULT_EQUITY for t in VALID_TRIPLES}
        set_triple = (M.SET, F.NONE, S.NONE)
        pair_triple = (M.PAIR, F.NONE, S.NONE)
        eq_full[set_triple] = 0.9
        eq_full[pair_triple] = 0.3

        result = calculate_ev_open(make_node_data(equity_vs_full=eq_full), [33])
        rows_by = {(r["made"], r["flush_draw"], r["straight_draw"]): r for r in result["rows"]}
        assert rows_by[("SET", "NONE", "NONE")]["evs"]["X"] > rows_by[("PAIR", "NONE", "NONE")]["evs"]["X"]

    def test_all_fold_means_bet_ev_equals_pot(self, make_node_data):
        node = make_node_data(fold_count=10, call_count=0, raise_count=0, pot_bb=10.0)
        result = calculate_ev_open(node, [33])
        for row in result["rows"]:
            assert row["evs"]["B33"] == pytest.approx(10.0)

    def test_best_action_is_highest_ev(self, make_node_data):
        result = calculate_ev_open(make_node_data(), [33, 66])
        for row in result["rows"]:
            best = row["best_action"]
            assert row["evs"][best] == max(row["evs"].values())


class TestEvVsBet:
    def test_returns_fold_call_raise(self, make_node_data):
        result = calculate_ev_vs_bet(make_node_data(), villain_bet_bb=3.0)
        assert result["available_actions"] == ["F", "C", "R"]

    def test_row_count_matches_valid_triples(self, make_node_data):
        result = calculate_ev_vs_bet(make_node_data(), villain_bet_bb=3.0)
        assert len(result["rows"]) == len(VALID_TRIPLES)

    def test_fold_ev_is_always_zero(self, make_node_data):
        result = calculate_ev_vs_bet(make_node_data(), villain_bet_bb=3.0)
        for row in result["rows"]:
            assert row["evs"]["F"] == 0.0

    def test_high_equity_prefers_call_over_fold(self, make_node_data):
        eq_call = {t: 0.9 for t in VALID_TRIPLES}
        result = calculate_ev_vs_bet(
            make_node_data(equity_vs_call=eq_call),
            villain_bet_bb=3.0,
        )
        for row in result["rows"]:
            assert row["evs"]["C"] > row["evs"]["F"]

    def test_zero_equity_prefers_fold(self, make_node_data):
        eq_call = {t: 0.0 for t in VALID_TRIPLES}
        eq_raise = {t: 0.0 for t in VALID_TRIPLES}
        result = calculate_ev_vs_bet(
            make_node_data(equity_vs_call=eq_call, equity_vs_raise=eq_raise, fold_count=0, call_count=10, raise_count=0),
            villain_bet_bb=3.0,
        )
        for row in result["rows"]:
            assert row["best_action"] == "F"

    def test_all_villain_fold_makes_raise_best(self, make_node_data):
        node = make_node_data(fold_count=10, call_count=0, raise_count=0, pot_bb=6.0)
        result = calculate_ev_vs_bet(node, villain_bet_bb=3.0)
        for row in result["rows"]:
            # villain always folds to raise -> win pot + their bet
            assert row["evs"]["R"] == pytest.approx(6.0 + 3.0)
            assert row["best_action"] == "R"

    def test_best_action_is_highest_ev(self, make_node_data):
        result = calculate_ev_vs_bet(make_node_data(), villain_bet_bb=3.0)
        for row in result["rows"]:
            best = row["best_action"]
            assert row["evs"][best] == max(row["evs"].values())
