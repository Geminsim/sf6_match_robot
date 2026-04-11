from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

# SQL queries for creating tables
CREATE_TOURNAMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS tournaments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id            INTEGER NOT NULL,
    channel_id          INTEGER NOT NULL,
    name                TEXT NOT NULL,
    created_by          INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'registration'
                        CHECK(status IN ('registration','in_progress','completed','cancelled')),
    registration_msg_id INTEGER,
    bracket_msg_ids     TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_tournament 
ON tournaments(channel_id) 
WHERE status IN ('registration', 'in_progress');
"""

CREATE_PARTICIPANTS_TABLE = """
CREATE TABLE IF NOT EXISTS participants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id   INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL,
    display_name    TEXT NOT NULL,
    seed            INTEGER,
    placement       INTEGER,
    eliminated_at   TEXT,
    registered_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tournament_id, user_id)
);
"""

CREATE_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS matches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id       INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    match_tag           TEXT NOT NULL,
    bracket             TEXT NOT NULL
                        CHECK(bracket IN ('winners','losers','grand_finals')),
    round_num           INTEGER NOT NULL,
    match_num           INTEGER NOT NULL,
    player1_id          INTEGER,
    player2_id          INTEGER,
    player1_score       INTEGER DEFAULT 0,
    player2_score       INTEGER DEFAULT 0,
    winner_id           INTEGER,
    loser_id            INTEGER,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','ready','in_progress','completed')),
    next_winner_match   TEXT,
    next_winner_slot    INTEGER,
    next_loser_match    TEXT,
    next_loser_slot     INTEGER,
    notification_msg_id INTEGER,
    reported_by         INTEGER,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT,
    UNIQUE(tournament_id, match_tag)
);
"""

async def init_db(database_url: str) -> None:
    """Initialize database tables."""
    # Strip sqlite:/// if present
    if database_url.startswith("sqlite:///"):
        # local file path
        db_path = database_url[10:]
    elif database_url.startswith("sqlite://"):
        db_path = database_url[9:]
    else:
        db_path = database_url

    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    log.info(f"Initializing database at {db_path}")

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.executescript(CREATE_TOURNAMENTS_TABLE)
        await db.execute(CREATE_PARTICIPANTS_TABLE)
        await db.execute(CREATE_MATCHES_TABLE)
        await db.commit()
    
    log.info("Database tables initialized successfully.")

# Expose a connection factory depending on the url if needed,
# or we can let the repo handle opening connections as needed.
@asynccontextmanager
async def get_db_connection(database_url: str):
    if database_url.startswith("sqlite:///"):
        db_path = database_url[10:]
    elif database_url.startswith("sqlite://"):
        db_path = database_url[9:]
    else:
        db_path = database_url
    
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = aiosqlite.Row
        yield conn

