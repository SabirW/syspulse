"""SQLite persistence: one row per run, one row per check result.

Uses the standard library's sqlite3 directly (no ORM) so the SQL itself
stays visible — this project is meant to show SQL, not hide it.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import CheckResult, Status

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname     TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    overall      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS check_results (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    name    TEXT NOT NULL,
    status  TEXT NOT NULL,
    detail  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_check_results_run_id ON check_results(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_hostname ON runs(hostname);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_run(
    conn: sqlite3.Connection,
    hostname: str,
    collected_at: str,
    overall: Status,
    results: list[CheckResult],
) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO runs (hostname, collected_at, overall) VALUES (?, ?, ?)",
            (hostname, collected_at, overall.value),
        )
        run_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO check_results (run_id, name, status, detail) VALUES (?, ?, ?, ?)",
            [(run_id, r.name, r.status.value, r.detail) for r in results],
        )
    return run_id


def get_run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()


def get_latest_run(conn: sqlite3.Connection, hostname: str | None = None) -> sqlite3.Row | None:
    if hostname:
        query = "SELECT * FROM runs WHERE hostname = ? ORDER BY id DESC LIMIT 1"
        return conn.execute(query, (hostname,)).fetchone()
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()


def get_results_for_run(conn: sqlite3.Connection, run_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT name, status, detail FROM check_results WHERE run_id = ? ORDER BY name",
        (run_id,),
    ).fetchall()


def get_history(conn: sqlite3.Connection, hostname: str, limit: int = 10) -> list[sqlite3.Row]:
    """Most recent runs for a host, newest first."""
    return conn.execute(
        "SELECT id, collected_at, overall FROM runs "
        "WHERE hostname = ? ORDER BY id DESC LIMIT ?",
        (hostname, limit),
    ).fetchall()
