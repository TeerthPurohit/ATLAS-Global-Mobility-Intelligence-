"""Postgres-backed conversation history store (FR-7), migrated off SQLite
per ADR-009's RDS operational store.

DuckDB is single-writer and already handles analytical warehouse queries.
Session history relies on frequent small inserts from potentially multiple
backend instances, so a shared Postgres connection replaces the
per-instance SQLite file (ADR-004, SPEC-008 FR-7).
"""
from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

TABLE_NAME = "messages"


def get_connection(conninfo: str | None = None) -> psycopg.Connection:
    dsn = conninfo or os.environ["DATABASE_URL"]
    sslrootcert = os.environ.get("POSTGRES_SSLROOTCERT", "certs/global-bundle.pem")
    return psycopg.connect(dsn, sslmode="verify-full", sslrootcert=sslrootcert, row_factory=dict_row)


def init_db(conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    with get_connection(conninfo) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                route TEXT,
                sql TEXT,
                timestamp TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_session ON {table_name}(session_id)")
        conn.commit()


def save_message(
    session_id: str,
    role: str,
    content: str,
    route: str | None = None,
    sql: str | None = None,
    conninfo: str | None = None,
    table_name: str = TABLE_NAME,
) -> None:
    init_db(conninfo, table_name)
    with get_connection(conninfo) as conn:
        conn.execute(
            f"""
            INSERT INTO {table_name} (session_id, role, content, route, sql)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, role, content, route, sql),
        )
        conn.commit()


def session_exists(session_id: str, conninfo: str | None = None, table_name: str = TABLE_NAME) -> bool:
    init_db(conninfo, table_name)
    with get_connection(conninfo) as conn:
        cur = conn.execute(f"SELECT 1 FROM {table_name} WHERE session_id = %s LIMIT 1", (session_id,))
        return cur.fetchone() is not None


def get_session_history(session_id: str, conninfo: str | None = None, table_name: str = TABLE_NAME) -> list[dict[str, Any]]:
    init_db(conninfo, table_name)
    with get_connection(conninfo) as conn:
        cur = conn.execute(
            f"""
            SELECT role, content, route, sql, timestamp
            FROM {table_name}
            WHERE session_id = %s
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = cur.fetchall()
        for row in rows:
            row["timestamp"] = row["timestamp"].isoformat()
        return rows
