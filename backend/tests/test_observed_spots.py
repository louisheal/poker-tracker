"""Tests for observed_spots pipeline: emitter, DB, queries, and service layer.

Uses 11 anonymised real hands in tests/hands/stats_panel.txt.
See plan/stats_panel/TESTS.md for scenario descriptions.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.db.importer import _insert_result
from app.db.queries import query_node_action_counts
from app.db.schema import init_db
from app.models.enums import BoardType
from app.parsers.core import parse_file
from app.services.street_stats import build_base_key, get_street_stats, NODE_SUFFIXES

HANDS_FILE = str(Path(__file__).parent / "hands" / "stats_panel.txt")


@pytest.fixture(scope="module")
def stats_db():
    result = parse_file(HANDS_FILE)
    conn = init_db(":memory:")
    _insert_result(conn, result)
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# T1: C-bet frequency (FLOP, OOP PFR)
# ---------------------------------------------------------------------------

def test_flop_cbet_oop_pfr(stats_db):
    r = query_node_action_counts(stats_db, "FLOP", hero_ip=False, hero_pfr=True)
    assert r["total"] == 5
    assert r["counts"]["B"] == 3
    assert r["counts"]["X"] == 2


# ---------------------------------------------------------------------------
# T2: Response to c-bet (FLOP_B, IP defender)
# ---------------------------------------------------------------------------

def test_flop_b_ip_defender(stats_db):
    r = query_node_action_counts(stats_db, "FLOP_B", hero_ip=True, hero_pfr=False)
    assert r["total"] == 3
    assert r["counts"]["F"] == 1
    assert r["counts"]["C"] == 1
    assert r["counts"]["R"] == 1


# ---------------------------------------------------------------------------
# T3: Turn stats after check-check flop (OOP PFR)
# ---------------------------------------------------------------------------

def test_turn_after_xx_flop(stats_db):
    r = query_node_action_counts(
        stats_db, "FLOP_X_X_TURN", hero_ip=False, hero_pfr=True,
    )
    assert r["total"] == 2
    assert r["counts"]["B"] == 2


# ---------------------------------------------------------------------------
# T4: Pool inclusion
# ---------------------------------------------------------------------------

def test_pool_excluded_by_default(stats_db):
    r = query_node_action_counts(stats_db, "FLOP", hero_ip=True)
    assert r["total"] == 4


def test_pool_included(stats_db):
    r = query_node_action_counts(stats_db, "FLOP", hero_ip=True, include_pool=True)
    assert r["total"] == 5


# ---------------------------------------------------------------------------
# T5: Board type filter
# ---------------------------------------------------------------------------

def test_board_type_all(stats_db):
    r = query_node_action_counts(stats_db, "FLOP")
    assert r["total"] == 10


def test_board_type_monotone(stats_db):
    r = query_node_action_counts(
        stats_db, "FLOP", board_types=[BoardType.MONOTONE],
    )
    assert r["total"] == 1


# ---------------------------------------------------------------------------
# T6: Service layer returns all 6 node keys
# ---------------------------------------------------------------------------

def test_service_returns_all_suffixes(stats_db):
    result = get_street_stats(stats_db, "FLOP", hero_ip=False, hero_pfr=True)
    assert set(result.keys()) == {f"FLOP{s}" for s in NODE_SUFFIXES}

    assert result["FLOP"]["total"] == 5
    assert result["FLOP_B"]["counts"]["C"] == 1
    assert result["FLOP_B"]["counts"]["F"] == 1
    assert result["FLOP_B"]["counts"]["R"] == 1
    assert result["FLOP_B_R"]["counts"]["F"] == 1
    assert result["FLOP_X"]["counts"]["X"] == 2
    assert result["FLOP_X_B"]["total"] == 0
    assert result["FLOP_X_B_R"]["total"] == 0


# ---------------------------------------------------------------------------
# T7: Terminal spots (showdown hands have NULL next_action)
# ---------------------------------------------------------------------------

def test_terminal_spots(stats_db):
    rows = stats_db.execute(
        "SELECT COUNT(*) FROM observed_spots WHERE next_action IS NULL",
    ).fetchone()
    assert rows[0] == 5


# ---------------------------------------------------------------------------
# T8: Date range filter
# ---------------------------------------------------------------------------

def test_date_filter_all(stats_db):
    r = query_node_action_counts(stats_db, "FLOP")
    assert r["total"] == 10


def test_date_filter_dec_2025(stats_db):
    r = query_node_action_counts(
        stats_db,
        "FLOP",
        start=date(2025, 12, 1),
        end=date(2025, 12, 31),
    )
    assert r["total"] == 8


# ---------------------------------------------------------------------------
# build_base_key unit tests
# ---------------------------------------------------------------------------

def test_build_base_key_flop_only():
    assert build_base_key() == "FLOP"


def test_build_base_key_flop_with_sequence():
    assert build_base_key("X_B_C") == "FLOP_X_B_C"


def test_build_base_key_turn():
    assert build_base_key("B_C", "") == "FLOP_B_C_TURN"


def test_build_base_key_turn_with_sequence():
    assert build_base_key("B_C", "X_B_C") == "FLOP_B_C_TURN_X_B_C"


def test_build_base_key_river():
    assert build_base_key("B_C", "X_B_C", "") == "FLOP_B_C_TURN_X_B_C_RIVER"


def test_build_base_key_river_with_sequence():
    assert build_base_key("B_C", "X", "B_C") == "FLOP_B_C_TURN_X_RIVER_B_C"
