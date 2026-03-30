import sqlite3


TABLES = {
    "file_imports": """
        CREATE TABLE IF NOT EXISTS file_imports (
            filename TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0
        )
    """,
    "range_events": """
        CREATE TABLE IF NOT EXISTS range_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            played_on TEXT NOT NULL,
            hand_key TEXT NOT NULL,
            position TEXT NOT NULL,
            action TEXT NOT NULL,
            pot_type TEXT NOT NULL,
            villain TEXT
        )
    """,
    "flop_events": """
        CREATE TABLE IF NOT EXISTS flop_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            played_on TEXT NOT NULL,
            pot_type TEXT NOT NULL,
            board_type INTEGER NOT NULL,
            hero_preflop_raiser INTEGER NOT NULL,
            hero_in_position INTEGER NOT NULL,
            cbet INTEGER NOT NULL,
            fold_to_cbet INTEGER NOT NULL,
            raise_to_cbet INTEGER NOT NULL,
            donk_bet INTEGER NOT NULL,
            fold_to_donk_bet INTEGER NOT NULL,
            raise_to_donk_bet INTEGER NOT NULL,
            cbet_size_pct REAL,
            donk_bet_size_pct REAL,
            is_pool INTEGER NOT NULL DEFAULT 0
        )
    """,
    "turn_events": """
        CREATE TABLE IF NOT EXISTS turn_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            played_on TEXT NOT NULL,
            pot_type TEXT NOT NULL,
            board_type INTEGER NOT NULL,
            hero_preflop_raiser INTEGER NOT NULL,
            hero_in_position INTEGER NOT NULL,
            flop_action_sequence TEXT NOT NULL,
            turn_runout TEXT NOT NULL,
            hero_bet_turn INTEGER NOT NULL,
            villain_fold_to_hero_bet INTEGER NOT NULL,
            villain_raise_to_hero_bet INTEGER NOT NULL,
            villain_bet_turn INTEGER NOT NULL,
            hero_fold_to_villain_bet INTEGER NOT NULL,
            hero_raise_to_villain_bet INTEGER NOT NULL,
            is_pool INTEGER NOT NULL DEFAULT 0
        )
    """,
    "river_events": """
        CREATE TABLE IF NOT EXISTS river_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            played_on TEXT NOT NULL,
            pot_type TEXT NOT NULL,
            board_type INTEGER NOT NULL,
            hero_in_position INTEGER NOT NULL,
            flop_action_sequence TEXT NOT NULL,
            flop_rank_texture TEXT NOT NULL,
            turn_runout TEXT NOT NULL,
            turn_action_sequence TEXT NOT NULL,
            river_runout TEXT NOT NULL,
            river_action_sequence TEXT NOT NULL,
            hero_bet_river INTEGER NOT NULL,
            villain_fold_to_hero_bet INTEGER NOT NULL,
            villain_raise_to_hero_bet INTEGER NOT NULL,
            villain_bet_river INTEGER NOT NULL,
            hero_fold_to_villain_bet INTEGER NOT NULL,
            hero_raise_to_villain_bet INTEGER NOT NULL,
            went_to_showdown INTEGER NOT NULL,
            showdown_type TEXT,
            hero_won_showdown INTEGER NOT NULL,
            pot_size_bb REAL NOT NULL,
            is_pool INTEGER NOT NULL DEFAULT 0
        )
    """,
    "line_events": """
        CREATE TABLE IF NOT EXISTS line_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            played_on TEXT NOT NULL,
            pot_type TEXT NOT NULL,
            board_type INTEGER NOT NULL,
            hero_in_position INTEGER NOT NULL,
            hero_preflop_raiser INTEGER NOT NULL,
            hero_pnl_bb REAL NOT NULL,
            hero_preflop_invested_bb REAL NOT NULL,
            pot_at_flop_bb REAL NOT NULL,
            pot_at_turn_bb REAL NOT NULL DEFAULT 0,
            pot_at_river_bb REAL NOT NULL DEFAULT 0,
            turn_runout TEXT,
            river_runout TEXT,
            flop_action_str TEXT NOT NULL DEFAULT '',
            turn_action_str TEXT NOT NULL DEFAULT '',
            river_action_str TEXT NOT NULL DEFAULT '',
            cbet INTEGER NOT NULL DEFAULT 0,
            fold_to_cbet INTEGER NOT NULL DEFAULT 0,
            raise_to_cbet INTEGER NOT NULL DEFAULT 0,
            donk_bet INTEGER NOT NULL DEFAULT 0,
            fold_to_donk_bet INTEGER NOT NULL DEFAULT 0,
            raise_to_donk_bet INTEGER NOT NULL DEFAULT 0,
            cbet_size_pct REAL,
            donk_bet_size_pct REAL,
            fold_to_cbet_raise INTEGER NOT NULL DEFAULT 0,
            fold_to_donk_raise INTEGER NOT NULL DEFAULT 0,
            hero_hand TEXT,
            villain_hand TEXT,
            flop_cards TEXT NOT NULL DEFAULT '',
            turn_card TEXT,
            river_card TEXT,
            is_pool INTEGER NOT NULL DEFAULT 0,
            -- Precomputed hand classifications per street
            flop_hero_made TEXT,
            flop_hero_flush_draw TEXT,
            flop_hero_straight_draw TEXT,
            flop_villain_made TEXT,
            flop_villain_flush_draw TEXT,
            flop_villain_straight_draw TEXT,
            turn_hero_made TEXT,
            turn_hero_flush_draw TEXT,
            turn_hero_straight_draw TEXT,
            turn_villain_made TEXT,
            turn_villain_flush_draw TEXT,
            turn_villain_straight_draw TEXT,
            river_hero_made TEXT,
            river_hero_flush_draw TEXT,
            river_hero_straight_draw TEXT,
            river_villain_made TEXT,
            river_villain_flush_draw TEXT,
            river_villain_straight_draw TEXT,
            -- Denormalised street stats (turn/river)
            turn_hero_bet INTEGER NOT NULL DEFAULT 0,
            turn_villain_fold INTEGER NOT NULL DEFAULT 0,
            turn_villain_raise INTEGER NOT NULL DEFAULT 0,
            turn_villain_bet INTEGER NOT NULL DEFAULT 0,
            turn_hero_fold INTEGER NOT NULL DEFAULT 0,
            turn_hero_raise INTEGER NOT NULL DEFAULT 0,
            river_hero_bet INTEGER NOT NULL DEFAULT 0,
            river_villain_fold INTEGER NOT NULL DEFAULT 0,
            river_villain_raise INTEGER NOT NULL DEFAULT 0,
            river_villain_bet INTEGER NOT NULL DEFAULT 0,
            river_hero_fold INTEGER NOT NULL DEFAULT 0,
            river_hero_raise INTEGER NOT NULL DEFAULT 0,
            -- First action per street
            flop_first_actor TEXT,
            flop_first_action TEXT,
            flop_first_size REAL,
            turn_first_actor TEXT,
            turn_first_action TEXT,
            turn_first_size REAL,
            river_first_actor TEXT,
            river_first_action TEXT,
            river_first_size REAL
        )
    """,
    "observed_spots": """
        CREATE TABLE IF NOT EXISTS observed_spots (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id      TEXT NOT NULL,
            node_key     TEXT NOT NULL,
            next_action  TEXT,
            hero_ip      INTEGER NOT NULL,
            hero_pfr     INTEGER NOT NULL,
            pot_type     INTEGER NOT NULL,
            board_type   INTEGER NOT NULL,
            turn_runout  INTEGER,
            river_runout INTEGER,
            played_on    TEXT NOT NULL,
            is_pool      INTEGER NOT NULL DEFAULT 0
        )
    """,
}

INDEXES = [
    # Flop events: filter by pool, pot, board, position, raiser, date
    """CREATE INDEX IF NOT EXISTS idx_flop_filters
       ON flop_events(is_pool, pot_type, board_type, hero_in_position, hero_preflop_raiser, played_on)""",

    # Turn events: filter + group by flop action sequence
    """CREATE INDEX IF NOT EXISTS idx_turn_filters
       ON turn_events(is_pool, pot_type, board_type, hero_in_position, hero_preflop_raiser, played_on)""",
    """CREATE INDEX IF NOT EXISTS idx_turn_sequence
       ON turn_events(flop_action_sequence)""",

    # River events: filter + group by river action sequence
    """CREATE INDEX IF NOT EXISTS idx_river_filters
       ON river_events(is_pool, pot_type, board_type, hero_in_position, played_on)""",
    """CREATE INDEX IF NOT EXISTS idx_river_sequence
       ON river_events(river_action_sequence)""",

    # Line events: main filter index
    """CREATE INDEX IF NOT EXISTS idx_line_filters
       ON line_events(is_pool, pot_type, board_type, hero_in_position, hero_preflop_raiser, played_on)""",
    # Line events: runout filtering
    """CREATE INDEX IF NOT EXISTS idx_line_turn_runout
       ON line_events(turn_runout)""",
    """CREATE INDEX IF NOT EXISTS idx_line_river_runout
       ON line_events(river_runout)""",

    # Observed spots: main lookup index
    """CREATE INDEX IF NOT EXISTS ix_spots_lookup
       ON observed_spots(node_key, hero_ip, hero_pfr, pot_type, board_type)""",
]


def init_db(db_path: str) -> sqlite3.Connection:
    """Create tables and indexes, return a connection."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    for ddl in TABLES.values():
        conn.execute(ddl)
    for idx in INDEXES:
        conn.execute(idx)
    conn.commit()
    return conn
