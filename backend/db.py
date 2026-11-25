"""The SQLite store for the claims' changing state."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend import data

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "undercover.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    running INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS decisions (
    claim_id TEXT PRIMARY KEY REFERENCES claims (claim_id),
    decision TEXT NOT NULL,
    payout REAL NOT NULL,
    explanation TEXT NOT NULL,
    policy_section TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    signed_off_at TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims (claim_id),
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims (claim_id),
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def database_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", DEFAULT_PATH))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the store, creating its tables and queue if empty, and commit on exit."""
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        with conn:
            if conn.execute("SELECT 1 FROM claims LIMIT 1").fetchone() is None:
                conn.executemany(
                    "INSERT INTO claims (claim_id) VALUES (?)",
                    [(claim["claim_id"],) for claim in data.claims()],
                )
            yield conn
    finally:
        conn.close()
