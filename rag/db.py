"""Shared SQLAlchemy engine for the Postgres operational store (ADR-009,
migrated from RDS to Neon 2026-08-28 -- see rag/session_store.py and
backend/services/{prediction_log,tariff_profiles}.py for the callers).

session_store.py, prediction_log.py, and tariff_profiles.py all write to the
same Postgres instance, so the Engine (and its connection pool, and the
sslmode/timeout connect args) is built once per process here instead of
duplicated per module. psycopg stays the underlying driver
(postgresql+psycopg:// dialect) -- only the raw-SQL-string call pattern is
what SQLAlchemy replaces.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _to_sqlalchemy_dsn(dsn: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if dsn.startswith(prefix):
            return "postgresql+psycopg://" + dsn[len(prefix):]
    return dsn


def build_engine(conninfo: str | None = None) -> Engine:
    dsn = conninfo or os.environ["DATABASE_URL"]
    # connect_timeout=3: without it, an unreachable Postgres instance blocks
    # on the OS-level TCP timeout (60s+) instead of failing fast into the
    # callers' degrade path.
    connect_args: dict = {"connect_timeout": 3}
    sslrootcert = os.environ.get("POSTGRES_SSLROOTCERT")
    if sslrootcert and Path(sslrootcert).exists():
        # Legacy RDS path: verify against its specific CA bundle explicitly.
        connect_args["sslmode"] = "verify-full"
        connect_args["sslrootcert"] = sslrootcert
    # else: no override -- the DSN's own sslmode/channel_binding query
    # params govern (Neon's connection string already specifies both, using
    # its publicly-trusted cert -- no custom root CA needed).
    return create_engine(_to_sqlalchemy_dsn(dsn), connect_args=connect_args, pool_pre_ping=True)


_default_engine: Engine | None = None


def get_engine(conninfo: str | None = None) -> Engine:
    global _default_engine
    if conninfo is not None:
        return build_engine(conninfo)
    if _default_engine is None:
        _default_engine = build_engine()
    return _default_engine


def get_connection(conninfo: str | None = None) -> Connection:
    return get_engine(conninfo).connect()
