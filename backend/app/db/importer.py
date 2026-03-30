"""Import parsed hand history events into SQLite."""
from __future__ import annotations

import json
import logging
import os
import sqlite3

from app.parsers import parse_file, FileParseResult
from app.parsers.hand_types import classify_made_hand, classify_flush_draw, classify_straight_draw

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _card_str(card) -> str:
    """Card -> 'Ah' style string."""
    return f"{card.rank.value}{card.suit.value.lower()}"


def _hole_cards_str(hc) -> str | None:
    if hc is None:
        return None
    return f"{_card_str(hc.fst_card)} {_card_str(hc.snd_card)}"


def _cards_str(cards: list) -> str:
    """List of Card -> space-separated string."""
    return " ".join(_card_str(c) for c in cards) if cards else ""


def _action_list_json(actions: list) -> str:
    """List of StreetAction -> compact JSON string."""
    if not actions:
        return ""
    return json.dumps(
        [[a.actor, a.action, a.size_pct] for a in actions],
        separators=(",", ":"),
    )


def _enum_val(e) -> str | None:
    if e is None:
        return None
    return e.value if hasattr(e, "value") else str(e)


# ---------------------------------------------------------------------------
# Hand classification helpers
# ---------------------------------------------------------------------------

def _classify(hole_cards, board: list) -> tuple[str | None, str | None, str | None]:
    """Return (made_hand, flush_draw, straight_draw) as strings, or Nones."""
    if hole_cards is None or not board:
        return None, None, None
    made = classify_made_hand(hole_cards, board).value
    flush = classify_flush_draw(hole_cards, board).value
    straight = classify_straight_draw(hole_cards, board).value
    return made, flush, straight


# ---------------------------------------------------------------------------
# Bulk insert helpers
# ---------------------------------------------------------------------------

_RANGE_COLS = (
    "played_on", "hand_key", "position", "action", "pot_type", "villain",
)

_FLOP_COLS = (
    "played_on", "pot_type", "board_type", "hero_preflop_raiser",
    "hero_in_position", "cbet", "fold_to_cbet", "raise_to_cbet",
    "donk_bet", "fold_to_donk_bet", "raise_to_donk_bet",
    "cbet_size_pct", "donk_bet_size_pct", "is_pool",
)

_TURN_COLS = (
    "played_on", "pot_type", "board_type", "hero_preflop_raiser",
    "hero_in_position", "flop_action_sequence", "turn_runout",
    "hero_bet_turn", "villain_fold_to_hero_bet", "villain_raise_to_hero_bet",
    "villain_bet_turn", "hero_fold_to_villain_bet", "hero_raise_to_villain_bet",
    "is_pool",
)

_RIVER_COLS = (
    "played_on", "pot_type", "board_type", "hero_in_position",
    "flop_action_sequence", "flop_rank_texture", "turn_runout",
    "turn_action_sequence", "river_runout", "river_action_sequence",
    "hero_bet_river", "villain_fold_to_hero_bet", "villain_raise_to_hero_bet",
    "villain_bet_river", "hero_fold_to_villain_bet", "hero_raise_to_villain_bet",
    "went_to_showdown", "showdown_type", "hero_won_showdown",
    "pot_size_bb", "is_pool",
)

_LINE_COLS = (
    "played_on", "pot_type", "board_type", "hero_in_position",
    "hero_preflop_raiser", "hero_pnl_bb", "hero_preflop_invested_bb",
    "pot_at_flop_bb", "pot_at_turn_bb", "pot_at_river_bb",
    "turn_runout", "river_runout",
    "flop_action_str", "turn_action_str", "river_action_str",
    "cbet", "fold_to_cbet", "raise_to_cbet",
    "donk_bet", "fold_to_donk_bet", "raise_to_donk_bet",
    "cbet_size_pct", "donk_bet_size_pct",
    "fold_to_cbet_raise", "fold_to_donk_raise",
    "hero_hand", "villain_hand", "flop_cards", "turn_card", "river_card",
    "is_pool",
    "flop_hero_made", "flop_hero_flush_draw", "flop_hero_straight_draw",
    "flop_villain_made", "flop_villain_flush_draw", "flop_villain_straight_draw",
    "turn_hero_made", "turn_hero_flush_draw", "turn_hero_straight_draw",
    "turn_villain_made", "turn_villain_flush_draw", "turn_villain_straight_draw",
    "river_hero_made", "river_hero_flush_draw", "river_hero_straight_draw",
    "river_villain_made", "river_villain_flush_draw", "river_villain_straight_draw",
    "turn_hero_bet", "turn_villain_fold", "turn_villain_raise",
    "turn_villain_bet", "turn_hero_fold", "turn_hero_raise",
    "river_hero_bet", "river_villain_fold", "river_villain_raise",
    "river_villain_bet", "river_hero_fold", "river_hero_raise",
    "flop_first_actor", "flop_first_action", "flop_first_size",
    "turn_first_actor", "turn_first_action", "turn_first_size",
    "river_first_actor", "river_first_action", "river_first_size",
)

_SPOT_COLS = (
    "hand_id", "node_key", "next_action",
    "hero_ip", "hero_pfr", "pot_type", "board_type",
    "turn_runout", "river_runout", "played_on", "is_pool",
)


def _insert_sql(table: str, cols: tuple[str, ...]) -> str:
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    return f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------

def _range_row(e) -> tuple:
    return (
        str(e.played_on),
        e.hand_key,
        _enum_val(e.position),
        e.action,
        _enum_val(e.pot_type),
        _enum_val(e.villain),
    )


def _flop_row(e) -> tuple:
    return (
        str(e.played_on),
        _enum_val(e.pot_type),
        e.board_type.value,
        int(e.hero_preflop_raiser),
        int(e.hero_in_position),
        int(e.cbet),
        int(e.fold_to_cbet),
        int(e.raise_to_cbet),
        int(e.donk_bet),
        int(e.fold_to_donk_bet),
        int(e.raise_to_donk_bet),
        e.cbet_size_pct,
        e.donk_bet_size_pct,
        int(e.is_pool),
    )


def _turn_row(e) -> tuple:
    return (
        str(e.played_on),
        _enum_val(e.pot_type),
        e.board_type.value,
        int(e.hero_preflop_raiser),
        int(e.hero_in_position),
        _enum_val(e.flop_action_sequence),
        _enum_val(e.turn_runout),
        int(e.hero_bet_turn),
        int(e.villain_fold_to_hero_bet),
        int(e.villain_raise_to_hero_bet),
        int(e.villain_bet_turn),
        int(e.hero_fold_to_villain_bet),
        int(e.hero_raise_to_villain_bet),
        int(e.is_pool),
    )


def _river_row(e) -> tuple:
    return (
        str(e.played_on),
        _enum_val(e.pot_type),
        e.board_type.value,
        int(e.hero_in_position),
        _enum_val(e.flop_action_sequence),
        _enum_val(e.flop_rank_texture),
        _enum_val(e.turn_runout),
        _enum_val(e.turn_action_sequence),
        _enum_val(e.river_runout),
        _enum_val(e.river_action_sequence),
        int(e.hero_bet_river),
        int(e.villain_fold_to_hero_bet),
        int(e.villain_raise_to_hero_bet),
        int(e.villain_bet_river),
        int(e.hero_fold_to_villain_bet),
        int(e.hero_raise_to_villain_bet),
        int(e.went_to_showdown),
        _enum_val(e.showdown_type),
        int(e.hero_won_showdown),
        e.pot_size_bb,
        int(e.is_pool),
    )


def _street_bools(actions: list) -> tuple[int, int, int, int, int, int]:
    """Extract hero/villain bet/fold/raise booleans from a list of StreetAction."""
    hero_bet = hero_fold = hero_raise = 0
    villain_bet = villain_fold = villain_raise = 0
    for a in actions:
        if a.actor == "hero":
            if a.action == "B":
                hero_bet = 1
            elif a.action == "F":
                hero_fold = 1
            elif a.action == "R":
                hero_raise = 1
        elif a.actor == "villain":
            if a.action == "B":
                villain_bet = 1
            elif a.action == "F":
                villain_fold = 1
            elif a.action == "R":
                villain_raise = 1
    return hero_bet, villain_fold, villain_raise, villain_bet, hero_fold, hero_raise


def _first_action(actions: list) -> tuple[str | None, str | None, float | None]:
    """Extract first action (actor, action, size_pct) from a list of StreetAction."""
    if not actions:
        return None, None, None
    a = actions[0]
    return a.actor, a.action, a.size_pct


def _line_row(e) -> tuple:
    flop_cards = list(e.flop_cards)
    turn_board = flop_cards + ([e.turn_card] if e.turn_card else [])
    river_board = turn_board + ([e.river_card] if e.river_card else [])

    if flop_cards:
        fhm, fhf, fhs = _classify(e.hero_hand, flop_cards)
        fvm, fvf, fvs = _classify(e.villain_hand, flop_cards)
    else:
        fhm = fhf = fhs = fvm = fvf = fvs = None
    thm, thf, ths = _classify(e.hero_hand, turn_board) if e.turn_card else (None, None, None)
    tvm, tvf, tvs = _classify(e.villain_hand, turn_board) if e.turn_card else (None, None, None)
    rhm, rhf, rhs = _classify(e.hero_hand, river_board) if e.river_card else (None, None, None)
    rvm, rvf, rvs = _classify(e.villain_hand, river_board) if e.river_card else (None, None, None)

    turn_bools = _street_bools(e.turn_actions)
    river_bools = _street_bools(e.river_actions)
    flop_fa = _first_action(e.flop_actions)
    turn_fa = _first_action(e.turn_actions)
    river_fa = _first_action(e.river_actions)

    return (
        str(e.played_on),
        _enum_val(e.pot_type),
        e.board_type.value,
        int(e.hero_in_position),
        int(e.hero_preflop_raiser),
        e.hero_pnl_bb,
        e.hero_preflop_invested_bb,
        e.pot_at_flop_bb,
        e.pot_at_turn_bb,
        e.pot_at_river_bb,
        _enum_val(e.turn_runout),
        _enum_val(e.river_runout),
        _action_list_json(e.flop_actions),
        _action_list_json(e.turn_actions),
        _action_list_json(e.river_actions),
        int(e.cbet),
        int(e.fold_to_cbet),
        int(e.raise_to_cbet),
        int(e.donk_bet),
        int(e.fold_to_donk_bet),
        int(e.raise_to_donk_bet),
        e.cbet_size_pct,
        e.donk_bet_size_pct,
        int(e.fold_to_cbet_raise),
        int(e.fold_to_donk_raise),
        _hole_cards_str(e.hero_hand),
        _hole_cards_str(e.villain_hand),
        _cards_str(e.flop_cards),
        _card_str(e.turn_card) if e.turn_card else None,
        _card_str(e.river_card) if e.river_card else None,
        int(e.is_pool),
        fhm, fhf, fhs, fvm, fvf, fvs,
        thm, thf, ths, tvm, tvf, tvs,
        rhm, rhf, rhs, rvm, rvf, rvs,
        *turn_bools, *river_bools,
        *flop_fa, *turn_fa, *river_fa,
    )


def _spot_row(s) -> tuple:
    return (
        s.hand_id,
        s.node_key,
        s.next_action.value if s.next_action else None,
        int(s.hero_ip),
        int(s.hero_pfr),
        _enum_val(s.pot_type),
        s.board_type.value,
        _enum_val(s.turn_runout),
        _enum_val(s.river_runout),
        str(s.played_on),
        int(s.is_pool),
    )


# ---------------------------------------------------------------------------
# Main import function
# ---------------------------------------------------------------------------

def _insert_result(conn: sqlite3.Connection, result: FileParseResult) -> int:
    """Insert all events from a FileParseResult into the DB. Returns total rows inserted."""
    rows = 0

    if result.range_events:
        conn.executemany(_insert_sql("range_events", _RANGE_COLS),
                         [_range_row(e) for e in result.range_events])
        rows += len(result.range_events)

    if result.cbet_events:
        conn.executemany(_insert_sql("flop_events", _FLOP_COLS),
                         [_flop_row(e) for e in result.cbet_events])
        rows += len(result.cbet_events)

    if result.turn_events:
        conn.executemany(_insert_sql("turn_events", _TURN_COLS),
                         [_turn_row(e) for e in result.turn_events])
        rows += len(result.turn_events)

    if result.river_events:
        conn.executemany(_insert_sql("river_events", _RIVER_COLS),
                         [_river_row(e) for e in result.river_events])
        rows += len(result.river_events)

    if result.line_events:
        conn.executemany(_insert_sql("line_events", _LINE_COLS),
                         [_line_row(e) for e in result.line_events])
        rows += len(result.line_events)

    if result.observed_spots:
        conn.executemany(_insert_sql("observed_spots", _SPOT_COLS),
                         [_spot_row(s) for s in result.observed_spots])
        rows += len(result.observed_spots)

    return rows


def import_hand_histories(conn: sqlite3.Connection, histories_dir: str) -> list[str]:
    """Scan hand history files and import new/modified ones into the DB.

    Returns list of distinct played_on dates (as ISO strings).
    """
    existing = {
        row["filename"]: row["mtime"]
        for row in conn.execute("SELECT filename, mtime FROM file_imports").fetchall()
    }

    txt_files = sorted(
        f for f in os.listdir(histories_dir)
        if f.endswith(".txt") and not f.startswith(".")
    )

    parsed_count = 0
    skipped_count = 0
    total_files = len(txt_files)
    to_parse = []

    for filename in txt_files:
        path = os.path.join(histories_dir, filename)
        mtime = os.path.getmtime(path)

        if filename in existing and existing[filename] == mtime:
            skipped_count += 1
            continue
        to_parse.append((filename, path, mtime))

    if not to_parse:
        logger.info(f"All {total_files} files already imported")
    else:
        logger.info(f"{len(to_parse)}/{total_files} files to parse")

    for filename, path, mtime in to_parse:
        parsed_count += 1
        logger.info(f"{parsed_count}/{len(to_parse)} files parsed")
        result = parse_file(path)

        # Remove old data for this file if re-importing
        if filename in existing:
            for table in ("range_events", "flop_events", "turn_events",
                          "river_events", "line_events", "observed_spots"):
                conn.execute(f"DELETE FROM {table} WHERE rowid IN "
                             f"(SELECT rowid FROM {table} LIMIT 0)")
            logger.warning(f"File {filename} modified -- full re-import recommended")

        row_count = _insert_result(conn, result)
        conn.execute(
            "INSERT OR REPLACE INTO file_imports (filename, mtime, row_count) VALUES (?, ?, ?)",
            (filename, mtime, row_count),
        )
        conn.commit()

    logger.info(f"Import complete: {parsed_count}/{total_files} files parsed")

    dates = [
        row[0]
        for row in conn.execute("SELECT DISTINCT played_on FROM line_events ORDER BY played_on").fetchall()
    ]
    return dates
