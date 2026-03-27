"""SQL query functions that replace the in-memory store aggregation methods."""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_RANK_MAP = {r.value: r for r in Rank}
_SUIT_MAP = {s.value.lower(): s for s in Suit}


def _parse_card(s: str) -> Card:
    """Parse 'Ah' -> Card(Rank.ACE, Suit.HEARTS)."""
    return Card(_RANK_MAP[s[0]], _SUIT_MAP[s[1]])


def _parse_hole_cards(s: str | None) -> HoleCards | None:
    if not s:
        return None
    parts = s.split()
    return HoleCards(_parse_card(parts[0]), _parse_card(parts[1]))


def _parse_cards(s: str | None) -> list[Card]:
    if not s:
        return []
    return [_parse_card(p) for p in s.split()]


def _card_to_json(s: str | None) -> dict | None:
    if not s:
        return None
    c = _parse_card(s)
    return c.to_json()


def _hole_cards_to_json(s: str | None) -> list[dict] | None:
    if not s:
        return None
    parts = s.split()
    return [_parse_card(p).to_json() for p in parts]


def _parse_actions_json(s: str) -> list[list]:
    """Parse compact JSON action string -> list of [actor, action, size_pct]."""
    if not s:
        return []
    return json.loads(s)


# ---------------------------------------------------------------------------
# WHERE clause builder
# ---------------------------------------------------------------------------

def _base_where(
    params: list,
    *,
    start: date | None = None,
    end: date | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    hero_in_position: list | None = None,
    hero_preflop_raiser: list | None = None,
    include_pool: bool = False,
    turn_runouts: list | None = None,
    river_runouts: list | None = None,
    flop_actions: list | None = None,
    flop_rank_textures: list | None = None,
    turn_action_sequences: list | None = None,
) -> str:
    """Build a WHERE clause from filter parameters. Appends bind values to params list."""
    clauses = []
    if not include_pool:
        clauses.append("is_pool = 0")
    if start:
        clauses.append("played_on >= ?")
        params.append(str(start))
    if end:
        clauses.append("played_on <= ?")
        params.append(str(end))
    if pot_types:
        placeholders = ",".join("?" for _ in pot_types)
        clauses.append(f"pot_type IN ({placeholders})")
        params.extend(t.value if hasattr(t, "value") else str(t) for t in pot_types)
    if board_types:
        placeholders = ",".join("?" for _ in board_types)
        clauses.append(f"board_type IN ({placeholders})")
        params.extend(b.value if hasattr(b, "value") else int(b) for b in board_types)
    if hero_in_position is not None and hero_in_position:
        placeholders = ",".join("?" for _ in hero_in_position)
        clauses.append(f"hero_in_position IN ({placeholders})")
        params.extend(int(b) for b in hero_in_position)
    if hero_preflop_raiser is not None and hero_preflop_raiser:
        placeholders = ",".join("?" for _ in hero_preflop_raiser)
        clauses.append(f"hero_preflop_raiser IN ({placeholders})")
        params.extend(int(b) for b in hero_preflop_raiser)
    if turn_runouts:
        placeholders = ",".join("?" for _ in turn_runouts)
        clauses.append(f"turn_runout IN ({placeholders})")
        params.extend(r.value if hasattr(r, "value") else str(r) for r in turn_runouts)
    if river_runouts:
        placeholders = ",".join("?" for _ in river_runouts)
        clauses.append(f"river_runout IN ({placeholders})")
        params.extend(r.value if hasattr(r, "value") else str(r) for r in river_runouts)
    if flop_actions:
        placeholders = ",".join("?" for _ in flop_actions)
        clauses.append(f"flop_action_sequence IN ({placeholders})")
        params.extend(a.value if hasattr(a, "value") else str(a) for a in flop_actions)
    if flop_rank_textures:
        placeholders = ",".join("?" for _ in flop_rank_textures)
        clauses.append(f"flop_rank_texture IN ({placeholders})")
        params.extend(t.value if hasattr(t, "value") else str(t) for t in flop_rank_textures)
    if turn_action_sequences:
        placeholders = ",".join("?" for _ in turn_action_sequences)
        clauses.append(f"turn_action_sequence IN ({placeholders})")
        params.extend(a.value if hasattr(a, "value") else str(a) for a in turn_action_sequences)

    return (" WHERE " + " AND ".join(clauses)) if clauses else ""


# ---------------------------------------------------------------------------
# Flop queries
# ---------------------------------------------------------------------------

def query_flop_stats(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    hero_in_position: list | None = None,
    hero_preflop_raiser: list | None = None,
    bet_size_min: float | None = None,
    bet_size_max: float | None = None,
    include_pool: bool = False,
) -> dict:
    params: list = []
    where = _base_where(
        params, start=start, end=end, pot_types=pot_types, board_types=board_types,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        include_pool=include_pool,
    )
    sql = f"""
        SELECT
            COUNT(*) as n,
            SUM(cbet) as cbet_n,
            SUM(CASE WHEN cbet THEN fold_to_cbet ELSE 0 END) as fold_to_cbet,
            SUM(CASE WHEN cbet THEN raise_to_cbet ELSE 0 END) as raise_to_cbet,
            SUM(donk_bet) as donk_n,
            SUM(CASE WHEN donk_bet THEN fold_to_donk_bet ELSE 0 END) as fold_to_donk,
            SUM(CASE WHEN donk_bet THEN raise_to_donk_bet ELSE 0 END) as raise_to_donk
        FROM flop_events{where}
    """
    row = conn.execute(sql, params).fetchone()
    n = row["n"] or 0
    cbet_n = row["cbet_n"] or 0
    donk_n = row["donk_n"] or 0
    raise_to_cbet = row["raise_to_cbet"] or 0
    raise_to_donk = row["raise_to_donk"] or 0

    return {
        "hand_count": n,
        "cbet_pct": (cbet_n / n * 100) if n else 0,
        "fold_to_cbet_pct": ((row["fold_to_cbet"] or 0) / cbet_n * 100) if cbet_n else 0,
        "raise_to_cbet_pct": (raise_to_cbet / cbet_n * 100) if cbet_n else 0,
        "donk_bet_pct": (donk_n / n * 100) if n else 0,
        "fold_to_donk_pct": ((row["fold_to_donk"] or 0) / donk_n * 100) if donk_n else 0,
        "raise_to_donk_pct": (raise_to_donk / donk_n * 100) if donk_n else 0,
    }


def query_flop_bet_sizes(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    hero_in_position: list | None = None,
    hero_preflop_raiser: list | None = None,
    include_pool: bool = False,
) -> list[float]:
    params: list = []
    where = _base_where(
        params, start=start, end=end, pot_types=pot_types, board_types=board_types,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        include_pool=include_pool,
    )
    # Only get sizes where there was a cbet
    extra = " AND cbet = 1 AND cbet_size_pct IS NOT NULL"
    if where:
        sql = f"SELECT cbet_size_pct FROM flop_events{where}{extra}"
    else:
        sql = f"SELECT cbet_size_pct FROM flop_events WHERE cbet = 1 AND cbet_size_pct IS NOT NULL"
        # rebuild without the extra since no where clause
        sql = f"SELECT cbet_size_pct FROM flop_events{where}"
        if where:
            sql += extra
        else:
            sql += " WHERE cbet = 1 AND cbet_size_pct IS NOT NULL"

    # Simpler approach
    params_copy: list = []
    where_clause = _base_where(
        params_copy, start=start, end=end, pot_types=pot_types, board_types=board_types,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        include_pool=include_pool,
    )
    if where_clause:
        sql = f"SELECT cbet_size_pct FROM flop_events{where_clause} AND cbet = 1 AND cbet_size_pct IS NOT NULL"
    else:
        sql = "SELECT cbet_size_pct FROM flop_events WHERE cbet = 1 AND cbet_size_pct IS NOT NULL"

    return [row[0] for row in conn.execute(sql, params_copy).fetchall()]


# ---------------------------------------------------------------------------
# Turn queries
# ---------------------------------------------------------------------------

def query_turn_stats(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    hero_in_position: list | None = None,
    hero_preflop_raiser: list | None = None,
    turn_runouts: list | None = None,
    include_pool: bool = False,
) -> dict:
    params: list = []
    where = _base_where(
        params, start=start, end=end, pot_types=pot_types, board_types=board_types,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        turn_runouts=turn_runouts, include_pool=include_pool,
    )
    sql = f"""
        SELECT
            flop_action_sequence,
            COUNT(*) as n,
            SUM(hero_bet_turn) as hero_bet,
            SUM(CASE WHEN hero_bet_turn THEN villain_fold_to_hero_bet ELSE 0 END) as v_fold,
            SUM(CASE WHEN hero_bet_turn THEN villain_raise_to_hero_bet ELSE 0 END) as v_raise,
            SUM(villain_bet_turn) as villain_bet,
            SUM(CASE WHEN villain_bet_turn THEN hero_fold_to_villain_bet ELSE 0 END) as h_fold,
            SUM(CASE WHEN villain_bet_turn THEN hero_raise_to_villain_bet ELSE 0 END) as h_raise
        FROM turn_events{where}
        GROUP BY flop_action_sequence
    """
    rows = conn.execute(sql, params).fetchall()
    row_map = {r["flop_action_sequence"]: r for r in rows}

    from app.models.enums import ActionSequence
    result = {}
    for seq in ActionSequence:
        r = row_map.get(seq.value)
        if not r or r["n"] == 0:
            result[seq.value] = {
                "hero_bet_pct": 0, "villain_fold_to_hero_bet_pct": 0, "villain_raise_to_hero_bet_pct": 0,
                "villain_bet_pct": 0, "hero_fold_to_villain_bet_pct": 0, "hero_raise_to_villain_bet_pct": 0,
                "hand_count": 0,
            }
            continue
        n = r["n"]
        hb = r["hero_bet"] or 0
        vb = r["villain_bet"] or 0
        result[seq.value] = {
            "hero_bet_pct": (hb / n * 100) if n else 0,
            "villain_fold_to_hero_bet_pct": ((r["v_fold"] or 0) / hb * 100) if hb else 0,
            "villain_raise_to_hero_bet_pct": ((r["v_raise"] or 0) / hb * 100) if hb else 0,
            "villain_bet_pct": (vb / n * 100) if n else 0,
            "hero_fold_to_villain_bet_pct": ((r["h_fold"] or 0) / vb * 100) if vb else 0,
            "hero_raise_to_villain_bet_pct": ((r["h_raise"] or 0) / vb * 100) if vb else 0,
            "hand_count": n,
        }
    return result


# ---------------------------------------------------------------------------
# River queries
# ---------------------------------------------------------------------------

def query_river_stats(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    hero_in_position: list | None = None,
    flop_actions: list | None = None,
    flop_rank_textures: list | None = None,
    turn_runouts: list | None = None,
    turn_action_sequences: list | None = None,
    river_runouts: list | None = None,
    include_pool: bool = False,
) -> dict:
    params: list = []
    where = _base_where(
        params, start=start, end=end, pot_types=pot_types, board_types=board_types,
        hero_in_position=hero_in_position, turn_runouts=turn_runouts,
        river_runouts=river_runouts, flop_actions=flop_actions,
        flop_rank_textures=flop_rank_textures,
        turn_action_sequences=turn_action_sequences,
        include_pool=include_pool,
    )

    # Action stats (overall)
    action_sql = f"""
        SELECT
            COUNT(*) as n,
            SUM(hero_bet_river) as hero_bet,
            SUM(CASE WHEN hero_bet_river THEN villain_fold_to_hero_bet ELSE 0 END) as v_fold,
            SUM(CASE WHEN hero_bet_river THEN villain_raise_to_hero_bet ELSE 0 END) as v_raise,
            SUM(villain_bet_river) as villain_bet,
            SUM(CASE WHEN villain_bet_river THEN hero_fold_to_villain_bet ELSE 0 END) as h_fold,
            SUM(CASE WHEN villain_bet_river THEN hero_raise_to_villain_bet ELSE 0 END) as h_raise
        FROM river_events{where}
    """
    ar = conn.execute(action_sql, params).fetchone()
    n = ar["n"] or 0
    hb = ar["hero_bet"] or 0
    vb = ar["villain_bet"] or 0

    # Per-sequence stats
    params2: list = []
    where2 = _base_where(
        params2, start=start, end=end, pot_types=pot_types, board_types=board_types,
        hero_in_position=hero_in_position, turn_runouts=turn_runouts,
        river_runouts=river_runouts, flop_actions=flop_actions,
        flop_rank_textures=flop_rank_textures,
        turn_action_sequences=turn_action_sequences,
        include_pool=include_pool,
    )
    seq_sql = f"""
        SELECT
            river_action_sequence,
            COUNT(*) as n,
            SUM(pot_size_bb) as total_pot,
            SUM(CASE WHEN went_to_showdown THEN 1 ELSE 0 END) as sd_n,
            SUM(CASE WHEN went_to_showdown AND hero_won_showdown THEN pot_size_bb
                 WHEN went_to_showdown THEN -pot_size_bb ELSE 0 END) as sd_bb
        FROM river_events{where2}
        GROUP BY river_action_sequence
    """
    seq_rows = conn.execute(seq_sql, params2).fetchall()
    seq_map = {r["river_action_sequence"]: r for r in seq_rows}

    from app.models.enums import ActionSequence
    showdown_result = {}
    avg_pot_result = {}
    for seq in ActionSequence:
        r = seq_map.get(seq.value)
        if not r or r["n"] == 0:
            avg_pot_result[seq.value] = {"avg_pot_bb": 0, "hand_count": 0}
            showdown_result[seq.value] = {"bb_per_hand": 0, "hand_count": 0}
            continue
        avg_pot_result[seq.value] = {
            "avg_pot_bb": round(r["total_pot"] / r["n"], 1),
            "hand_count": r["n"],
        }
        sd_n = r["sd_n"] or 0
        showdown_result[seq.value] = {
            "bb_per_hand": round(r["sd_bb"] / sd_n, 2) if sd_n else 0,
            "hand_count": sd_n,
        }

    return {
        "actions": {
            "hero_bet_pct": (hb / n * 100) if n else 0,
            "villain_fold_to_hero_bet_pct": ((ar["v_fold"] or 0) / hb * 100) if hb else 0,
            "villain_raise_to_hero_bet_pct": ((ar["v_raise"] or 0) / hb * 100) if hb else 0,
            "villain_bet_pct": (vb / n * 100) if n else 0,
            "hero_fold_to_villain_bet_pct": ((ar["h_fold"] or 0) / vb * 100) if vb else 0,
            "hero_raise_to_villain_bet_pct": ((ar["h_raise"] or 0) / vb * 100) if vb else 0,
            "hand_count": n,
        },
        "showdown": showdown_result,
        "avg_pot": avg_pot_result,
    }


# ---------------------------------------------------------------------------
# Volume query
# ---------------------------------------------------------------------------

def query_hand_volume(
    conn: sqlite3.Connection,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    params: list = []
    clauses = []
    if start:
        clauses.append("played_on >= ?")
        params.append(str(start))
    if end:
        clauses.append("played_on <= ?")
        params.append(str(end))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT played_on, COUNT(*) as cnt FROM line_events{where} GROUP BY played_on ORDER BY played_on"
    return [{"date": r[0], "count": r[1]} for r in conn.execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Ranges query
# ---------------------------------------------------------------------------

def query_ranges(
    conn: sqlite3.Connection,
    start: date | None = None,
    end: date | None = None,
) -> list[sqlite3.Row]:
    params: list = []
    clauses = []
    if start:
        clauses.append("played_on >= ?")
        params.append(str(start))
    if end:
        clauses.append("played_on <= ?")
        params.append(str(end))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT hand_key, position, action, pot_type, villain FROM range_events{where}"
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Line events queries (spot_stats, ev_node_data, hand_type_distribution)
# These use SQL for filtering, then Python for complex logic
# ---------------------------------------------------------------------------

def _line_where(
    params: list,
    *,
    start: date | None = None,
    end: date | None = None,
    hero_in_position: bool | None = None,
    hero_preflop_raiser: bool | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    turn_runouts: list | None = None,
    river_runouts: list | None = None,
    include_pool: bool = False,
) -> str:
    """Build WHERE clause for line_events using LineFilter fields."""
    clauses = []
    if not include_pool:
        clauses.append("is_pool = 0")
    if start:
        clauses.append("played_on >= ?")
        params.append(str(start))
    if end:
        clauses.append("played_on <= ?")
        params.append(str(end))
    if hero_in_position is not None:
        clauses.append("hero_in_position = ?")
        params.append(int(hero_in_position))
    if hero_preflop_raiser is not None:
        clauses.append("hero_preflop_raiser = ?")
        params.append(int(hero_preflop_raiser))
    if pot_types:
        placeholders = ",".join("?" for _ in pot_types)
        clauses.append(f"pot_type IN ({placeholders})")
        params.extend(t.value if hasattr(t, "value") else str(t) for t in pot_types)
    if board_types:
        placeholders = ",".join("?" for _ in board_types)
        clauses.append(f"board_type IN ({placeholders})")
        params.extend(b.value if hasattr(b, "value") else int(b) for b in board_types)
    if turn_runouts:
        placeholders = ",".join("?" for _ in turn_runouts)
        clauses.append(f"turn_runout IN ({placeholders})")
        params.extend(r.value if hasattr(r, "value") else str(r) for r in turn_runouts)
    if river_runouts:
        placeholders = ",".join("?" for _ in river_runouts)
        clauses.append(f"river_runout IN ({placeholders})")
        params.extend(r.value if hasattr(r, "value") else str(r) for r in river_runouts)
    return (" WHERE " + " AND ".join(clauses)) if clauses else ""


def _fetch_line_events(
    conn: sqlite3.Connection,
    columns: str,
    *,
    start: date | None = None,
    end: date | None = None,
    hero_in_position: bool | None = None,
    hero_preflop_raiser: bool | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    turn_runouts: list | None = None,
    river_runouts: list | None = None,
    include_pool: bool = False,
) -> list[sqlite3.Row]:
    params: list = []
    where = _line_where(
        params, start=start, end=end,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        pot_types=pot_types, board_types=board_types,
        turn_runouts=turn_runouts, river_runouts=river_runouts,
        include_pool=include_pool,
    )
    sql = f"SELECT {columns} FROM line_events{where}"
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Line events: spot_stats
# ---------------------------------------------------------------------------

BET_SIZE_BINS = [(0, 50), (50, 100), (100, 200)]
ACTION_ORDER = [
    "X", "B0-50", "B50-100", "B100-200", "B200+",
    "C", "R0-50", "R50-100", "R100-200", "R200+", "F",
]


def _action_sort_key(action: str) -> int:
    try:
        return ACTION_ORDER.index(action)
    except ValueError:
        return len(ACTION_ORDER)


def _filter_by_street_prefix(rows: list, street: str, prefix: list[str]) -> list:
    """Filter rows by action prefix on a given street. Works with sqlite3.Row objects."""
    action_col = {"flop": "flop_action_str", "turn": "turn_action_str", "river": "river_action_str"}[street]
    result = []
    for row in rows:
        actions = _parse_actions_json(row[action_col])
        if len(actions) < len(prefix):
            continue
        match = True
        for i, p in enumerate(prefix):
            a_action = actions[i][1]
            a_size = actions[i][2]
            if p in ("X", "F", "C"):
                if a_action != p:
                    match = False
                    break
            elif p.startswith("B") or p.startswith("R"):
                if a_action != p[0]:
                    match = False
                    break
                size_part = p[1:]
                if size_part and a_size is not None:
                    if size_part.endswith("+"):
                        lo = float(size_part[:-1])
                        if a_size < lo:
                            match = False
                            break
                    else:
                        parts = size_part.split("-")
                        if len(parts) == 2:
                            lo, hi = float(parts[0]), float(parts[1])
                            if not (lo <= a_size < hi):
                                match = False
                                break
            else:
                match = False
                break
        if match:
            result.append(row)
    return result


def _compute_next_actions(rows: list, depth: int, actions_col: str) -> list[dict]:
    """Compute action distribution at a given depth."""
    action_groups: dict[str, list[float]] = {}
    for row in rows:
        actions = _parse_actions_json(row[actions_col])
        if depth < len(actions):
            a_action = actions[depth][1]
            a_size = actions[depth][2]
            pnl = row["hero_pnl_bb"]
            if a_action in ("B", "R") and a_size is not None:
                placed = False
                for lo, hi in BET_SIZE_BINS:
                    if lo <= a_size < hi:
                        key = f"{a_action}{lo}-{hi}"
                        action_groups.setdefault(key, []).append(pnl)
                        placed = True
                        break
                if not placed:
                    key = f"{a_action}200+"
                    action_groups.setdefault(key, []).append(pnl)
            else:
                action_groups.setdefault(a_action, []).append(pnl)

    result = []
    for action in sorted(action_groups, key=_action_sort_key):
        pnls = action_groups[action]
        result.append({
            "action": action,
            "ev": sum(pnls) / len(pnls) if pnls else 0,
            "count": len(pnls),
        })
    return result


def _compute_flop_stats_from_rows(rows: list) -> dict:
    n = len(rows)
    cbet_n = sum(1 for r in rows if r["cbet"])
    fold_to_cbet = sum(1 for r in rows if r["cbet"] and r["fold_to_cbet"])
    raise_to_cbet = sum(1 for r in rows if r["cbet"] and r["raise_to_cbet"])
    fold_to_cbet_raise = sum(1 for r in rows if r["cbet"] and r["fold_to_cbet_raise"])
    donk_n = sum(1 for r in rows if r["donk_bet"])
    fold_to_donk = sum(1 for r in rows if r["donk_bet"] and r["fold_to_donk_bet"])
    raise_to_donk = sum(1 for r in rows if r["donk_bet"] and r["raise_to_donk_bet"])
    fold_to_donk_raise = sum(1 for r in rows if r["donk_bet"] and r["fold_to_donk_raise"])
    return {
        "cbet_pct": (cbet_n / n * 100) if n else 0,
        "fold_to_cbet_pct": (fold_to_cbet / cbet_n * 100) if cbet_n else 0,
        "raise_to_cbet_pct": (raise_to_cbet / cbet_n * 100) if cbet_n else 0,
        "fold_to_cbet_raise_pct": (fold_to_cbet_raise / max(1, raise_to_cbet) * 100) if cbet_n else 0,
        "donk_bet_pct": (donk_n / n * 100) if n else 0,
        "fold_to_donk_pct": (fold_to_donk / donk_n * 100) if donk_n else 0,
        "raise_to_donk_pct": (raise_to_donk / donk_n * 100) if donk_n else 0,
        "fold_to_donk_raise_pct": (fold_to_donk_raise / max(1, raise_to_donk) * 100) if donk_n else 0,
    }


def _compute_street_stats_from_rows(rows: list, actions_col: str) -> dict:
    """Compute hero/villain bet/fold/raise stats by scanning action JSON."""
    n = len(rows)
    hero_bet_n = 0
    villain_fold_to_hero = 0
    villain_raise_to_hero = 0
    villain_bet_n = 0
    hero_fold_to_villain = 0
    hero_raise_to_villain = 0

    for row in rows:
        actions = _parse_actions_json(row[actions_col])
        if not actions:
            continue
        hero_bet = villain_bet = False
        hero_fold = hero_raise = villain_fold = villain_raise = False
        for a in actions:
            actor, action = a[0], a[1]
            if actor == "hero" and action == "B":
                hero_bet = True
            elif actor == "villain" and action == "B":
                villain_bet = True
            elif actor == "hero" and action == "F":
                hero_fold = True
            elif actor == "hero" and action == "R":
                hero_raise = True
            elif actor == "villain" and action == "F":
                villain_fold = True
            elif actor == "villain" and action == "R":
                villain_raise = True
        if hero_bet:
            hero_bet_n += 1
            if villain_fold:
                villain_fold_to_hero += 1
            if villain_raise:
                villain_raise_to_hero += 1
        if villain_bet:
            villain_bet_n += 1
            if hero_fold:
                hero_fold_to_villain += 1
            if hero_raise:
                hero_raise_to_villain += 1

    return {
        "hero_bet_pct": (hero_bet_n / n * 100) if n else 0,
        "villain_fold_to_hero_bet_pct": (villain_fold_to_hero / hero_bet_n * 100) if hero_bet_n else 0,
        "villain_raise_to_hero_bet_pct": (villain_raise_to_hero / hero_bet_n * 100) if hero_bet_n else 0,
        "villain_bet_pct": (villain_bet_n / n * 100) if n else 0,
        "hero_fold_to_villain_bet_pct": (hero_fold_to_villain / villain_bet_n * 100) if villain_bet_n else 0,
        "hero_raise_to_villain_bet_pct": (hero_raise_to_villain / villain_bet_n * 100) if villain_bet_n else 0,
    }


EMPTY_FLOP_STATS = {k: 0 for k in ["cbet_pct", "fold_to_cbet_pct", "raise_to_cbet_pct", "fold_to_cbet_raise_pct", "donk_bet_pct", "fold_to_donk_pct", "raise_to_donk_pct", "fold_to_donk_raise_pct"]}
EMPTY_STREET_STATS = {k: 0 for k in ["hero_bet_pct", "villain_fold_to_hero_bet_pct", "villain_raise_to_hero_bet_pct", "villain_bet_pct", "hero_fold_to_villain_bet_pct", "hero_raise_to_villain_bet_pct"]}


def query_spot_stats(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    hero_in_position: bool | None = None,
    hero_preflop_raiser: bool | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    turn_runouts: list | None = None,
    river_runouts: list | None = None,
    include_pool: bool = False,
    flop_actions: list[str] | None = None,
    turn_actions: list[str] | None = None,
    river_actions: list[str] | None = None,
) -> dict:
    columns = (
        "hero_pnl_bb, hero_hand, villain_hand, flop_cards, turn_card, river_card, "
        "flop_action_str, turn_action_str, river_action_str, "
        "cbet, fold_to_cbet, raise_to_cbet, fold_to_cbet_raise, "
        "donk_bet, fold_to_donk_bet, raise_to_donk_bet, fold_to_donk_raise"
    )
    rows = _fetch_line_events(
        conn, columns, start=start, end=end,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        pot_types=pot_types, board_types=board_types,
        turn_runouts=turn_runouts, river_runouts=river_runouts,
        include_pool=include_pool,
    )

    # Apply action prefix filters in Python
    if flop_actions:
        rows = _filter_by_street_prefix(rows, "flop", flop_actions)

    on_turn = turn_actions is not None
    if on_turn:
        rows = [r for r in rows if r["turn_action_str"]]
        if turn_actions:
            rows = _filter_by_street_prefix(rows, "turn", turn_actions)

    on_river = river_actions is not None
    if on_river:
        rows = [r for r in rows if r["river_action_str"]]
        if river_actions:
            rows = _filter_by_street_prefix(rows, "river", river_actions)

    # Determine current street and depth
    if on_river:
        street = "river"
        depth = len(river_actions) if river_actions else 0
        actions_col = "river_action_str"
    elif on_turn:
        street = "turn"
        depth = len(turn_actions) if turn_actions else 0
        actions_col = "turn_action_str"
    else:
        street = "flop"
        depth = len(flop_actions) if flop_actions else 0
        actions_col = "flop_action_str"

    n = len(rows)
    if n == 0:
        return {
            "hand_count": 0,
            "street": street,
            "street_stats": EMPTY_FLOP_STATS.copy() if street == "flop" else EMPTY_STREET_STATS.copy(),
            "ev_stats": {"overall_ev": 0, "next_actions": []},
            "bet_sizes": [],
            "next_actor": None,
            "action_depth": depth,
            "flop_complete": on_turn or on_river,
            "turn_available": False,
            "turn_complete": on_river,
            "river_available": False,
            "top_wins": [],
            "top_losses": [],
        }

    # Single pass for overall_ev, top wins/losses, bet_sizes, next_actor, availability
    import heapq
    TOP_N = 5
    pnl_sum = 0.0
    # Use (pnl, index) tuples so equal pnl values never compare dicts
    top_wins: list[tuple[float, int]] = []
    top_losses: list[tuple[float, int]] = []
    turn_available = False
    river_available = False
    next_actor: str | None = None
    bet_sizes: list[float] = []

    for i, row in enumerate(rows):
        pnl = row["hero_pnl_bb"]
        pnl_sum += pnl

        if len(top_wins) < TOP_N:
            heapq.heappush(top_wins, (pnl, i))
        elif pnl > top_wins[0][0]:
            heapq.heapreplace(top_wins, (pnl, i))

        if len(top_losses) < TOP_N:
            heapq.heappush(top_losses, (-pnl, i))
        elif -pnl > top_losses[0][0]:
            heapq.heapreplace(top_losses, (-pnl, i))

        if not turn_available and row["turn_action_str"]:
            turn_available = True
        if not river_available and row["river_action_str"]:
            river_available = True

        actions = _parse_actions_json(row[actions_col])
        if depth < len(actions):
            if next_actor is None:
                next_actor = actions[depth][0]
            a_action = actions[depth][1]
            a_size = actions[depth][2]
            if a_action in ("B", "R") and a_size is not None:
                bet_sizes.append(a_size)

    overall_ev = pnl_sum / n

    next_actions = _compute_next_actions(rows, depth, actions_col)
    flop_complete = (not on_turn and not on_river and not next_actions and turn_available) or on_turn or on_river
    turn_complete = (on_turn and not on_river and not next_actions and river_available) or on_river

    # Build hand_result dicts only for the top N wins/losses (not every row)
    def _row_to_hand_result(row: sqlite3.Row) -> dict:
        return {
            "pnl_bb": round(row["hero_pnl_bb"], 2),
            "hero_hand": _hole_cards_to_json(row["hero_hand"]),
            "villain_hand": _hole_cards_to_json(row["villain_hand"]),
            "flop": [_parse_card(c).to_json() for c in row["flop_cards"].split()] if row["flop_cards"] else [],
            "turn_card": _card_to_json(row["turn_card"]),
            "river_card": _card_to_json(row["river_card"]),
        }

    # Compute street stats for the current street only
    if street == "flop":
        street_stats = _compute_flop_stats_from_rows(rows)
    else:
        street_stats = _compute_street_stats_from_rows(rows, actions_col)

    return {
        "hand_count": n,
        "street": street,
        "street_stats": street_stats,
        "ev_stats": {
            "overall_ev": overall_ev,
            "next_actions": next_actions,
        },
        "bet_sizes": [round(s, 1) for s in bet_sizes],
        "next_actor": next_actor,
        "action_depth": depth,
        "flop_complete": flop_complete,
        "turn_available": turn_available,
        "turn_complete": turn_complete,
        "river_available": river_available,
        "top_wins": sorted([_row_to_hand_result(rows[idx]) for _, idx in top_wins], key=lambda x: -x["pnl_bb"]),
        "top_losses": sorted([_row_to_hand_result(rows[idx]) for _, idx in top_losses], key=lambda x: x["pnl_bb"]),
    }


# ---------------------------------------------------------------------------
# Line events: ev_node_data
# ---------------------------------------------------------------------------

def query_ev_node_data(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    hero_in_position: bool | None = None,
    hero_preflop_raiser: bool | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    turn_runouts: list | None = None,
    river_runouts: list | None = None,
    include_pool: bool = False,
    flop_actions: list[str] | None = None,
    turn_actions: list[str] | None = None,
    river_actions: list[str] | None = None,
) -> dict:
    from app.parsers.equity import get_equity, VALID_TRIPLES

    columns = (
        "flop_action_str, turn_action_str, river_action_str, "
        "pot_at_flop_bb, pot_at_turn_bb, pot_at_river_bb, "
        "villain_hand, flop_cards, turn_card, river_card"
    )
    rows = _fetch_line_events(
        conn, columns, start=start, end=end,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        pot_types=pot_types, board_types=board_types,
        turn_runouts=turn_runouts, river_runouts=river_runouts,
        include_pool=include_pool,
    )

    # Apply action prefix filters
    if flop_actions:
        rows = _filter_by_street_prefix(rows, "flop", flop_actions)
    on_turn = turn_actions is not None
    if on_turn:
        rows = [r for r in rows if r["turn_action_str"]]
        if turn_actions:
            rows = _filter_by_street_prefix(rows, "turn", turn_actions)
    on_river = river_actions is not None
    if on_river:
        rows = [r for r in rows if r["river_action_str"]]
        if river_actions:
            rows = _filter_by_street_prefix(rows, "river", river_actions)

    POT_COL = {"river": "pot_at_river_bb", "turn": "pot_at_turn_bb", "flop": "pot_at_flop_bb"}

    if on_river:
        street = "river"
        depth = len(river_actions) if river_actions else 0
        actions_col = "river_action_str"
    elif on_turn:
        street = "turn"
        depth = len(turn_actions) if turn_actions else 0
        actions_col = "turn_action_str"
    else:
        street = "flop"
        depth = len(flop_actions) if flop_actions else 0
        actions_col = "flop_action_str"

    pot_col = POT_COL[street]

    # Find next_actor
    next_actor = None
    for row in rows:
        actions = _parse_actions_json(row[actions_col])
        if depth < len(actions):
            next_actor = actions[depth][0]
            break

    DEFAULT_EQUITY = 0.5
    n = len(rows)

    if next_actor is None:
        pot_bb = sum(row[pot_col] for row in rows) / n if n else 0
        return {
            "equity_vs_full": {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
            "equity_vs_call": {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
            "equity_vs_raise": {t: DEFAULT_EQUITY for t in VALID_TRIPLES},
            "fold_count": 0, "call_count": 0, "raise_count": 0,
            "median_raise_size_pct": None,
            "pot_bb": pot_bb, "street": street,
            "hand_count": n, "next_actor": None,
            "hero_faces_bet": False, "villain_bet_bb": None,
        }

    # Running sums
    full_eq_sum = {t: 0.0 for t in VALID_TRIPLES}
    call_eq_sum = {t: 0.0 for t in VALID_TRIPLES}
    raise_eq_sum = {t: 0.0 for t in VALID_TRIPLES}
    full_count = call_shown_count = raise_shown_count = 0
    fold_count = call_count = raise_count = 0
    raise_sizes: list[float] = []
    pot_sum = 0.0
    hero_faces_bet = False
    villain_bet_size_pct = None
    check_faces_bet = next_actor == "hero" and depth > 0

    for row in rows:
        pot_sum += row[pot_col]
        actions = _parse_actions_json(row[actions_col])
        if depth >= len(actions):
            continue

        if check_faces_bet and villain_bet_size_pct is None:
            prev = actions[depth - 1]
            if prev[0] == "villain" and prev[1] in ("B", "R") and prev[2] is not None:
                hero_faces_bet = True
                villain_bet_size_pct = prev[2]

        v_triple = None
        if row["villain_hand"]:
            vh = _parse_hole_cards(row["villain_hand"])
            board = _parse_cards(row["flop_cards"])
            if on_turn and row["turn_card"]:
                board.append(_parse_card(row["turn_card"]))
            if on_river and row["river_card"]:
                board.append(_parse_card(row["river_card"]))
            if vh and board:
                from app.parsers.hand_types import classify_made_hand as cmh, classify_flush_draw as cfd, classify_straight_draw as csd
                v_triple = (cmh(vh, board), cfd(vh, board), csd(vh, board))
                full_count += 1
                for hero in VALID_TRIPLES:
                    full_eq_sum[hero] += get_equity(hero, v_triple, street)

        hero_action = actions[depth]
        if hero_action[1] not in ("B", "R"):
            continue

        reaction = None
        for idx in range(depth + 1, len(actions)):
            if actions[idx][0] == "villain":
                reaction = actions[idx]
                break

        if reaction is None:
            if len(actions) > depth + 1:
                fold_count += 1
            continue

        if reaction[1] == "F":
            fold_count += 1
        elif reaction[1] in ("C", "X"):
            call_count += 1
        elif reaction[1] in ("R", "B"):
            raise_count += 1
            if reaction[2] is not None:
                raise_sizes.append(reaction[2])

        if v_triple is not None:
            if reaction[1] in ("C", "X"):
                call_shown_count += 1
                for hero in VALID_TRIPLES:
                    call_eq_sum[hero] += get_equity(hero, v_triple, street)
            elif reaction[1] in ("R", "B"):
                raise_shown_count += 1
                for hero in VALID_TRIPLES:
                    raise_eq_sum[hero] += get_equity(hero, v_triple, street)

    equity_vs_full = {t: (full_eq_sum[t] / full_count if full_count else DEFAULT_EQUITY) for t in VALID_TRIPLES}
    equity_vs_call = {t: (call_eq_sum[t] / call_shown_count if call_shown_count else DEFAULT_EQUITY) for t in VALID_TRIPLES}
    equity_vs_raise = {t: (raise_eq_sum[t] / raise_shown_count if raise_shown_count else DEFAULT_EQUITY) for t in VALID_TRIPLES}
    median_raise = sorted(raise_sizes)[len(raise_sizes) // 2] if raise_sizes else None
    pot_bb = pot_sum / n if n else 0
    villain_bet_bb = (villain_bet_size_pct / 100) * pot_bb if hero_faces_bet and villain_bet_size_pct is not None else None

    return {
        "equity_vs_full": equity_vs_full,
        "equity_vs_call": equity_vs_call,
        "equity_vs_raise": equity_vs_raise,
        "fold_count": fold_count,
        "call_count": call_count,
        "raise_count": raise_count,
        "median_raise_size_pct": median_raise,
        "pot_bb": pot_bb,
        "street": street,
        "hand_count": n,
        "next_actor": next_actor,
        "hero_faces_bet": hero_faces_bet,
        "villain_bet_bb": villain_bet_bb,
    }


# ---------------------------------------------------------------------------
# Line events: hand_type_distribution
# ---------------------------------------------------------------------------

def query_hand_type_distribution(
    conn: sqlite3.Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    hero_in_position: bool | None = None,
    hero_preflop_raiser: bool | None = None,
    pot_types: list | None = None,
    board_types: list | None = None,
    turn_runouts: list | None = None,
    river_runouts: list | None = None,
    include_pool: bool = False,
    flop_actions: list[str] | None = None,
    turn_actions: list[str] | None = None,
    river_actions: list[str] | None = None,
) -> dict:
    # Determine which street's classifications to use
    on_turn = turn_actions is not None
    on_river = river_actions is not None

    if on_river:
        hero_made_col = "river_hero_made"
        villain_made_col = "river_villain_made"
    elif on_turn:
        hero_made_col = "turn_hero_made"
        villain_made_col = "turn_villain_made"
    else:
        hero_made_col = "flop_hero_made"
        villain_made_col = "flop_villain_made"

    # We need action strings for prefix filtering and the precomputed columns
    columns = (
        f"flop_action_str, turn_action_str, river_action_str, "
        f"{hero_made_col}, {villain_made_col}"
    )
    rows = _fetch_line_events(
        conn, columns, start=start, end=end,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        pot_types=pot_types, board_types=board_types,
        turn_runouts=turn_runouts, river_runouts=river_runouts,
        include_pool=include_pool,
    )

    if flop_actions:
        rows = _filter_by_street_prefix(rows, "flop", flop_actions)
    if on_turn:
        rows = [r for r in rows if r["turn_action_str"]]
        if turn_actions:
            rows = _filter_by_street_prefix(rows, "turn", turn_actions)
    if on_river:
        rows = [r for r in rows if r["river_action_str"]]
        if river_actions:
            rows = _filter_by_street_prefix(rows, "river", river_actions)

    from app.models.enums import MadeHandType, DrawType

    hero_made = {t.value: 0 for t in MadeHandType}
    hero_draws = {t.value: 0 for t in DrawType}
    villain_made = {t.value: 0 for t in MadeHandType}
    villain_draws = {t.value: 0 for t in DrawType}

    # For draws we still need the full classification columns
    if on_river:
        hero_fd_col = "river_hero_flush_draw"
        hero_sd_col = "river_hero_straight_draw"
        villain_fd_col = "river_villain_flush_draw"
        villain_sd_col = "river_villain_straight_draw"
    elif on_turn:
        hero_fd_col = "turn_hero_flush_draw"
        hero_sd_col = "turn_hero_straight_draw"
        villain_fd_col = "turn_villain_flush_draw"
        villain_sd_col = "turn_villain_straight_draw"
    else:
        hero_fd_col = "flop_hero_flush_draw"
        hero_sd_col = "flop_hero_straight_draw"
        villain_fd_col = "flop_villain_flush_draw"
        villain_sd_col = "flop_villain_straight_draw"

    # Re-fetch with draw columns too
    columns2 = (
        f"flop_action_str, turn_action_str, river_action_str, "
        f"{hero_made_col}, {villain_made_col}, "
        f"{hero_fd_col}, {hero_sd_col}, {villain_fd_col}, {villain_sd_col}"
    )
    rows = _fetch_line_events(
        conn, columns2, start=start, end=end,
        hero_in_position=hero_in_position, hero_preflop_raiser=hero_preflop_raiser,
        pot_types=pot_types, board_types=board_types,
        turn_runouts=turn_runouts, river_runouts=river_runouts,
        include_pool=include_pool,
    )
    if flop_actions:
        rows = _filter_by_street_prefix(rows, "flop", flop_actions)
    if on_turn:
        rows = [r for r in rows if r["turn_action_str"]]
        if turn_actions:
            rows = _filter_by_street_prefix(rows, "turn", turn_actions)
    if on_river:
        rows = [r for r in rows if r["river_action_str"]]
        if river_actions:
            rows = _filter_by_street_prefix(rows, "river", river_actions)

    for row in rows:
        hm = row[hero_made_col]
        vm = row[villain_made_col]
        if hm:
            hero_made[hm] = hero_made.get(hm, 0) + 1
            hfd = row[hero_fd_col]
            hsd = row[hero_sd_col]
            hero_draws[_draw_type(hfd, hsd)] = hero_draws.get(_draw_type(hfd, hsd), 0) + 1
        if vm:
            villain_made[vm] = villain_made.get(vm, 0) + 1
            vfd = row[villain_fd_col]
            vsd = row[villain_sd_col]
            villain_draws[_draw_type(vfd, vsd)] = villain_draws.get(_draw_type(vfd, vsd), 0) + 1

    return {
        "hero": {"made_hands": hero_made, "draws": hero_draws},
        "villain": {"made_hands": villain_made, "draws": villain_draws},
    }


def _draw_type(flush_draw: str | None, straight_draw: str | None) -> str:
    """Combine flush and straight draw classifications into a DrawType value."""
    has_flush = flush_draw and flush_draw not in ("NONE", None)
    has_oesd = straight_draw == "OESD"
    has_gutshot = straight_draw == "GUTSHOT"

    if has_flush and has_oesd:
        return "FLUSH_OESD"
    if has_flush and has_gutshot:
        return "FLUSH_GUTSHOT"
    if has_flush:
        return "FLUSH_DRAW"
    if has_oesd:
        return "OESD"
    if has_gutshot:
        return "GUTSHOT"
    return "NO_DRAW"
