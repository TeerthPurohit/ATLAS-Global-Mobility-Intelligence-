"""SQLite-backed conversation history store (FR-7).

DuckDB is single-writer and already handles analytical warehouse queries.
Session history relies on frequent small inserts, so stdlib `sqlite3` is used
to avoid DuckDB lock contention (ADR-004, SPEC-008 FR-7).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "session_history.db"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target = Path(db_path) if db_path else DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                route TEXT,
                sql TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        conn.commit()
    finally:
        conn.close()


def save_message(
    session_id: str,
    role: str,
    content: str,
    route: str | None = None,
    sql: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO messages (session_id, role, content, route, sql)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, route, sql),
        )
        conn.commit()
    finally:
        conn.close()


def session_exists(session_id: str, db_path: Path | str | None = None) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT 1 FROM messages WHERE session_id = ? LIMIT 1", (session_id,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def get_session_history(session_id: str, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT role, content, route, sql, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = cur.fetchall()
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "route": row["route"],
                "sql": row["sql"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
    finally:
        conn.close()
