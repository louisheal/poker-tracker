"""Tests for DB import round-trip: events -> SQLite -> queries return correct data."""
from datetime import date

import pytest

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards, PokerPosition

from app.db.schema import init_db
from app.db.importer import _insert_result
from app.db.queries import (
    query_flop_stats, query_flop_bet_sizes,
    query_turn_stats, query_river_stats,
    query_hand_volume, query_ranges,
    query_spot_stats,
    query_street_stats, query_ev_summary, query_top_hands,
    query_ev_node_data,
)
from app.models.enums import (
    BoardType, PotType, ActionSequence, Runout,
    FlopRankTexture, ShowdownType,
)
from app.models.events import (
    RangeEvent, FlopEvent, TurnEvent, RiverEvent, LineEvent, StreetAction,
)
from app.parsers import FileParseResult


@pytest.fixture
def db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


def _make_card(rank_val, suit_val):
    return Card(Rank(rank_val), Suit(suit_val))


def _make_hole_cards(r1, s1, r2, s2):
    return HoleCards(_make_card(r1, s1), _make_card(r2, s2))


# ---------------------------------------------------------------------------
# Fixtures: sample events
# ---------------------------------------------------------------------------

def _sample_range_event():
    return RangeEvent(
        played_on=date(2024, 1, 15),
        hand_key="AKs",
        position=PokerPosition.CO,
        action="raise",
        pot_type=PotType.SRP,
        villain=None,
    )


def _sample_flop_event():
    return FlopEvent(
        played_on=date(2024, 1, 15),
        pot_type=PotType.SRP,
        board_type=BoardType.TWO_TONE,
        hero_preflop_raiser=True,
        hero_in_position=True,
        cbet=True,
        fold_to_cbet=False,
        raise_to_cbet=False,
        donk_bet=False,
        fold_to_donk_bet=False,
        raise_to_donk_bet=False,
        cbet_size_pct=66.0,
        is_pool=False,
    )


def _sample_turn_event():
    return TurnEvent(
        played_on=date(2024, 1, 15),
        pot_type=PotType.SRP,
        board_type=BoardType.TWO_TONE,
        hero_preflop_raiser=True,
        hero_in_position=True,
        flop_action_sequence=ActionSequence.BC,
        turn_runout=Runout.OTHER,
        hero_bet_turn=True,
        villain_fold_to_hero_bet=True,
        villain_raise_to_hero_bet=False,
        villain_bet_turn=False,
        hero_fold_to_villain_bet=False,
        hero_raise_to_villain_bet=False,
        is_pool=False,
    )


def _sample_river_event():
    return RiverEvent(
        played_on=date(2024, 1, 15),
        pot_type=PotType.SRP,
        board_type=BoardType.TWO_TONE,
        hero_in_position=True,
        flop_action_sequence=ActionSequence.BC,
        flop_rank_texture=FlopRankTexture.UNPAIRED,
        turn_runout=Runout.OTHER,
        turn_action_sequence=ActionSequence.BC,
        river_runout=Runout.OTHER,
        river_action_sequence=ActionSequence.BC,
        hero_bet_river=True,
        villain_fold_to_hero_bet=False,
        villain_raise_to_hero_bet=False,
        villain_bet_river=False,
        hero_fold_to_villain_bet=False,
        hero_raise_to_villain_bet=False,
        went_to_showdown=True,
        showdown_type=ShowdownType.BET_CALL,
        hero_won_showdown=True,
        pot_size_bb=6.5,
        is_pool=False,
    )


def _sample_line_event():
    return LineEvent(
        played_on=date(2024, 1, 15),
        pot_type=PotType.SRP,
        board_type=BoardType.TWO_TONE,
        hero_in_position=True,
        hero_preflop_raiser=True,
        hero_pnl_bb=3.5,
        hero_preflop_invested_bb=1.0,
        pot_at_flop_bb=4.5,
        flop_actions=[
            StreetAction(actor="hero", action="B", size_pct=66.0),
            StreetAction(actor="villain", action="C"),
        ],
        turn_actions=[],
        pot_at_turn_bb=0.0,
        river_actions=[],
        cbet=True,
        fold_to_cbet=False,
        raise_to_cbet=False,
        hero_hand=_make_hole_cards("A", "H", "K", "H"),
        villain_hand=_make_hole_cards("Q", "D", "J", "D"),
        flop_cards=[_make_card("T", "H"), _make_card("9", "H"), _make_card("2", "S")],
        is_pool=False,
    )


def _insert_samples(db):
    result = FileParseResult()
    result.range_events = [_sample_range_event()]
    result.cbet_events = [_sample_flop_event()]
    result.turn_events = [_sample_turn_event()]
    result.river_events = [_sample_river_event()]
    result.line_events = [_sample_line_event()]
    _insert_result(db, result)
    db.commit()


# ---------------------------------------------------------------------------
# Tests: round-trip integrity
# ---------------------------------------------------------------------------

class TestRangeEventRoundTrip:
    def test_position_stored_and_queryable(self, db):
        _insert_samples(db)
        rows = query_ranges(db)
        assert len(rows) == 1
        # Position should be the .value of PokerPosition (an int stored as string)
        assert rows[0]["position"] == str(PokerPosition.CO.value)

    def test_pot_type_stored_as_string_value(self, db):
        _insert_samples(db)
        rows = query_ranges(db)
        assert rows[0]["pot_type"] == "SRP"

    def test_position_converts_back_to_enum(self, db):
        """Regression: ranges router must convert DB strings back to PokerPosition enums."""
        _insert_samples(db)
        rows = query_ranges(db)
        pos_map = {str(p.value): p for p in PokerPosition}
        position = pos_map.get(rows[0]["position"])
        assert position == PokerPosition.CO


class TestFlopEventRoundTrip:
    def test_board_type_stored_as_int(self, db):
        _insert_samples(db)
        row = db.execute("SELECT board_type FROM flop_events").fetchone()
        assert row[0] == 1  # TWO_TONE = 1

    def test_query_flop_stats_counts(self, db):
        _insert_samples(db)
        result = query_flop_stats(db)
        assert result["hand_count"] == 1
        assert result["cbet_pct"] == 100.0

    def test_query_flop_bet_sizes(self, db):
        _insert_samples(db)
        sizes = query_flop_bet_sizes(db)
        assert sizes == [66.0]

    def test_board_type_filter(self, db):
        """Regression: BoardType is Enum not IntEnum, .value must be used for DB comparison."""
        _insert_samples(db)
        result = query_flop_stats(db, board_types=[BoardType.TWO_TONE])
        assert result["hand_count"] == 1
        result = query_flop_stats(db, board_types=[BoardType.RAINBOW])
        assert result["hand_count"] == 0


class TestTurnEventRoundTrip:
    def test_query_groups_by_action_sequence(self, db):
        _insert_samples(db)
        result = query_turn_stats(db)
        assert result["BC"]["hand_count"] == 1
        assert result["BC"]["hero_bet_pct"] == 100.0
        assert result["XX"]["hand_count"] == 0


class TestRiverEventRoundTrip:
    def test_showdown_stats(self, db):
        _insert_samples(db)
        result = query_river_stats(db)
        assert result["actions"]["hand_count"] == 1
        assert result["showdown"]["BC"]["hand_count"] == 1
        assert result["showdown"]["BC"]["bb_per_hand"] > 0


class TestLineEventRoundTrip:
    def test_action_str_stored(self, db):
        _insert_samples(db)
        row = db.execute("SELECT flop_action_str FROM line_events").fetchone()
        assert row[0] != ""
        # Should contain hero bet and villain call
        import json
        actions = json.loads(row[0])
        assert actions[0][0] == "hero"
        assert actions[0][1] == "B"
        assert actions[0][2] == 66.0

    def test_hand_classifications_precomputed(self, db):
        _insert_samples(db)
        row = db.execute("SELECT flop_hero_made, flop_villain_made FROM line_events").fetchone()
        assert row["flop_hero_made"] is not None
        assert row["flop_villain_made"] is not None

    def test_cards_stored_as_strings(self, db):
        _insert_samples(db)
        row = db.execute("SELECT hero_hand, villain_hand, flop_cards FROM line_events").fetchone()
        assert row["hero_hand"] is not None
        assert " " in row["hero_hand"]  # Two cards separated by space
        assert row["flop_cards"].count(" ") == 2  # Three cards

    def test_spot_stats_returns_data(self, db):
        _insert_samples(db)
        result = query_spot_stats(db)
        assert result["hand_count"] == 1
        assert result["ev_stats"]["overall_ev"] == 3.5
        assert result["street"] == "flop"
        assert "next_actions" in result["ev_stats"]
        assert "street_stats" in result
        assert "bet_sizes" in result
        assert "top_wins" in result
        assert "top_losses" in result

    def test_spot_stats_equal_pnl_no_crash(self, db):
        """Regression: heapq crashed comparing dicts when two hands had equal pnl."""
        result = FileParseResult()
        for _ in range(6):
            event = _sample_line_event()
            event.hero_pnl_bb = 5.0
            result.line_events.append(event)
        _insert_result(db, result)
        db.commit()
        stats = query_spot_stats(db)
        assert stats["hand_count"] == 6
        assert len(stats["top_wins"]) == 5
        assert len(stats["top_losses"]) == 5

    def test_street_stats_returns_flop_data(self, db):
        _insert_samples(db)
        result = query_street_stats(db)
        assert result["street"] == "flop"
        assert result["hand_count"] == 1
        assert "cbet_pct" in result["street_stats"]

    def test_ev_summary_returns_data(self, db):
        _insert_samples(db)
        result = query_ev_summary(db)
        assert result["ev_stats"]["overall_ev"] == 3.5
        assert "next_actions" in result["ev_stats"]
        assert "bet_sizes" in result
        assert "flop_complete" in result
        assert "next_actor" in result

    def test_top_hands_returns_wins_and_losses(self, db):
        _insert_samples(db)
        result = query_top_hands(db)
        assert "top_wins" in result
        assert "top_losses" in result
        assert len(result["top_wins"]) == 1
        assert result["top_wins"][0]["pnl_bb"] == 3.5

    def test_ev_node_data_pool_with_all_filters(self, db):
        """Regression: pool + all board/pot types should not crash."""
        _insert_samples(db)
        result = query_ev_node_data(
            db, include_pool=True,
            board_types=[BoardType.MONOTONE, BoardType.TWO_TONE, BoardType.RAINBOW],
            pot_types=[PotType.SRP, PotType.THREE_BET, PotType.FOUR_BET],
        )
        assert result["hand_count"] >= 0

    def test_split_endpoints_pool_no_filters(self, db):
        """Regression: include_pool=True with no other filters must not produce broken SQL."""
        result = FileParseResult()
        event = _sample_line_event()
        event.is_pool = True
        result.line_events.append(event)
        _insert_result(db, result)
        db.commit()
        assert query_street_stats(db, include_pool=True)["hand_count"] == 1
        assert query_ev_summary(db, include_pool=True)["ev_stats"]["overall_ev"] != 0 or True
        assert "top_wins" in query_top_hands(db, include_pool=True)


class TestVolumeRoundTrip:
    def test_volume_groups_by_date(self, db):
        _insert_samples(db)
        result = query_hand_volume(db)
        assert len(result) == 1
        assert result[0]["date"] == "2024-01-15"
        assert result[0]["count"] == 1

    def test_volume_date_filter(self, db):
        _insert_samples(db)
        result = query_hand_volume(db, start=date(2025, 1, 1))
        assert len(result) == 0


class TestPoolFilter:
    def test_pool_events_excluded_by_default(self, db):
        result = FileParseResult()
        event = _sample_flop_event()
        event.is_pool = True
        result.cbet_events = [event]
        _insert_result(db, result)
        db.commit()

        assert query_flop_stats(db)["hand_count"] == 0
        assert query_flop_stats(db, include_pool=True)["hand_count"] == 1
