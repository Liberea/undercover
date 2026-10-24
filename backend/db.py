"""The UnderCover database: a SQLite file, one connection per request."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Annotated

from fastapi import Depends

DEFAULT_PATH = Path(__file__).parent / "undercover.db"

SCHEMA = """
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    status TEXT NOT NULL,
    thread_id TEXT,
    data TEXT NOT NULL
);
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE decisions (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    outcome TEXT NOT NULL,
    payout REAL NOT NULL,
    reasons TEXT NOT NULL,
    policy_section TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    paid_amount REAL,
    paid_at TEXT,
    signed_off_by TEXT REFERENCES handlers
);
CREATE TABLE steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    """Return the database file, from UNDERCOVER_DB if set."""
    return Path(os.environ.get("UNDERCOVER_DB", DEFAULT_PATH))


def connect() -> sqlite3.Connection:
    """Open a connection that returns rows by column name."""
    connection = sqlite3.connect(db_path(), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def get_db() -> Iterator[sqlite3.Connection]:
    """Give a request its own connection, committed when the request succeeds."""
    with closing(connect()) as connection, connection:
        yield connection


Db = Annotated[sqlite3.Connection, Depends(get_db)]
