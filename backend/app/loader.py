import logging
import os
import sqlite3

from app.db.schema import init_db
from app.db.importer import import_hand_histories

logger = logging.getLogger(__name__)

DB_FILENAME = "poker.db"


def load_hand_histories(histories_dir: str | None = None) -> str:
    """Initialise the SQLite DB, import new hand history files, return DB path."""
    if histories_dir is None:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_dir = os.path.dirname(backend_dir)
        histories_dir = os.path.normpath(os.path.join(project_dir, "hand_histories"))

    db_path = os.path.join(histories_dir, DB_FILENAME)
    logger.info(f"Opening database at {db_path}")
    conn = init_db(db_path)

    if os.path.isdir(histories_dir):
        import_hand_histories(conn, histories_dir)

    row_counts = {}
    for table in ("range_events", "flop_events", "turn_events", "river_events", "line_events"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        row_counts[table] = count

    logger.info(
        f"Database ready: {row_counts['range_events']} range, "
        f"{row_counts['flop_events']} flop, {row_counts['turn_events']} turn, "
        f"{row_counts['river_events']} river, {row_counts['line_events']} line events"
    )

    conn.close()
    return db_path
