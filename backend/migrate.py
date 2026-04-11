"""Migration script: add denormalised columns to line_events.

Adds 21 new columns:
- 12 street stats booleans (turn/river hero/villain bet/fold/raise)
- 9 first-action columns (flop/turn/river first actor/action/size)

Then backfills them by parsing the existing JSON action strings.

Usage: cd backend && .\venv\Scripts\python.exe migrate.py
"""
import json
import logging
import os
import sqlite3
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 10_000

NEW_COLUMNS = [
    # Turn street stats (booleans)
    ("turn_hero_bet", "INTEGER NOT NULL DEFAULT 0"),
    ("turn_villain_fold", "INTEGER NOT NULL DEFAULT 0"),
    ("turn_villain_raise", "INTEGER NOT NULL DEFAULT 0"),
    ("turn_villain_bet", "INTEGER NOT NULL DEFAULT 0"),
    ("turn_hero_fold", "INTEGER NOT NULL DEFAULT 0"),
    ("turn_hero_raise", "INTEGER NOT NULL DEFAULT 0"),
    # River street stats (booleans)
    ("river_hero_bet", "INTEGER NOT NULL DEFAULT 0"),
    ("river_villain_fold", "INTEGER NOT NULL DEFAULT 0"),
    ("river_villain_raise", "INTEGER NOT NULL DEFAULT 0"),
    ("river_villain_bet", "INTEGER NOT NULL DEFAULT 0"),
    ("river_hero_fold", "INTEGER NOT NULL DEFAULT 0"),
    ("river_hero_raise", "INTEGER NOT NULL DEFAULT 0"),
    # First action per street
    ("flop_first_actor", "TEXT"),
    ("flop_first_action", "TEXT"),
    ("flop_first_size", "REAL"),
    ("turn_first_actor", "TEXT"),
    ("turn_first_action", "TEXT"),
    ("turn_first_size", "REAL"),
    ("river_first_actor", "TEXT"),
    ("river_first_action", "TEXT"),
    ("river_first_size", "REAL"),
]


def _parse_street_bools(actions_json: str) -> dict[str, bool]:
    """Parse action JSON and extract hero/villain bet/fold/raise booleans."""
    hero_bet = hero_fold = hero_raise = False
    villain_bet = villain_fold = villain_raise = False

    if not actions_json:
        return {
            "hero_bet": False, "hero_fold": False, "hero_raise": False,
            "villain_bet": False, "villain_fold": False, "villain_raise": False,
        }

    actions = json.loads(actions_json)
    for a in actions:
        actor, action = a[0], a[1]
        if actor == "hero":
            if action == "B":
                hero_bet = True
            elif action == "F":
                hero_fold = True
            elif action == "R":
                hero_raise = True
        elif actor == "villain":
            if action == "B":
                villain_bet = True
            elif action == "F":
                villain_fold = True
            elif action == "R":
                villain_raise = True

    return {
        "hero_bet": hero_bet, "hero_fold": hero_fold, "hero_raise": hero_raise,
        "villain_bet": villain_bet, "villain_fold": villain_fold, "villain_raise": villain_raise,
    }


def _parse_first_action(actions_json: str) -> tuple[str | None, str | None, float | None]:
    """Extract first action (actor, action, size) from action JSON."""
    if not actions_json:
        return None, None, None
    actions = json.loads(actions_json)
    if not actions:
        return None, None, None
    first = actions[0]
    return first[0], first[1], first[2] if len(first) > 2 else None


def add_columns(conn: sqlite3.Connection) -> int:
    """Add new columns if they don't already exist. Returns number of columns added."""
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(line_events)").fetchall()
    }
    added = 0
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE line_events ADD COLUMN {col_name} {col_type}")
            added += 1
    conn.commit()
    return added


def backfill(conn: sqlite3.Connection) -> None:
    """Backfill the new columns by parsing action JSON strings."""
    total = conn.execute("SELECT COUNT(*) FROM line_events").fetchone()[0]
    if total == 0:
        logger.info("No rows to backfill")
        return

    logger.info(f"Backfilling {total:,} rows...")
    t0 = time.perf_counter()

    cursor = conn.execute(
        "SELECT id, turn_action_str, river_action_str, flop_action_str "
        "FROM line_events"
    )

    batch = []
    processed = 0

    for row in cursor:
        row_id = row[0]
        turn_json = row[1]
        river_json = row[2]
        flop_json = row[3]

        turn_bools = _parse_street_bools(turn_json)
        river_bools = _parse_street_bools(river_json)
        flop_fa, flop_fact, flop_fs = _parse_first_action(flop_json)
        turn_fa, turn_fact, turn_fs = _parse_first_action(turn_json)
        river_fa, river_fact, river_fs = _parse_first_action(river_json)

        batch.append((
            int(turn_bools["hero_bet"]), int(turn_bools["villain_fold"]),
            int(turn_bools["villain_raise"]), int(turn_bools["villain_bet"]),
            int(turn_bools["hero_fold"]), int(turn_bools["hero_raise"]),
            int(river_bools["hero_bet"]), int(river_bools["villain_fold"]),
            int(river_bools["villain_raise"]), int(river_bools["villain_bet"]),
            int(river_bools["hero_fold"]), int(river_bools["hero_raise"]),
            flop_fa, flop_fact, flop_fs,
            turn_fa, turn_fact, turn_fs,
            river_fa, river_fact, river_fs,
            row_id,
        ))

        if len(batch) >= BATCH_SIZE:
            _flush_batch(conn, batch)
            processed += len(batch)
            batch = []
            elapsed = time.perf_counter() - t0
            logger.info(f"{processed:,}/{total:,} rows updated ({elapsed:.1f}s)")

    if batch:
        _flush_batch(conn, batch)
        processed += len(batch)

    conn.commit()
    elapsed = time.perf_counter() - t0
    logger.info(f"Backfill complete: {processed:,} rows in {elapsed:.1f}s")


def _flush_batch(conn: sqlite3.Connection, batch: list[tuple]) -> None:
    conn.executemany(
        """UPDATE line_events SET
            turn_hero_bet=?, turn_villain_fold=?, turn_villain_raise=?,
            turn_villain_bet=?, turn_hero_fold=?, turn_hero_raise=?,
            river_hero_bet=?, river_villain_fold=?, river_villain_raise=?,
            river_villain_bet=?, river_hero_fold=?, river_hero_raise=?,
            flop_first_actor=?, flop_first_action=?, flop_first_size=?,
            turn_first_actor=?, turn_first_action=?, turn_first_size=?,
            river_first_actor=?, river_first_action=?, river_first_size=?
        WHERE id=?""",
        batch,
    )


def main() -> None:
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(backend_dir)
    db_path = os.path.join(project_dir, "hand_histories", "poker.db")

    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return

    logger.info(f"Opening {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    added = add_columns(conn)
    if added > 0:
        logger.info(f"Added {added} new columns")
    else:
        logger.info("All columns already exist")

    backfill(conn)
    conn.close()
    logger.info("Migration complete")


if __name__ == "__main__":
    main()
