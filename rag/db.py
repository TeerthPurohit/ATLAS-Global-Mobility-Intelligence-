"""Shared SQLAlchemy engine for the Postgres operational store (ADR-009).

session_store.py and prediction_log.py both write to the same RDS instance,
so the Engine (and its connection pool, and the sslmode/timeout connect
args) is built once per process here instead of duplicated per module.
psycopg stays the underlying driver (postgresql+psycopg:// dialect) -- only
the raw-SQL-string call pattern is what SQLAlchemy replaces.
"""
from __future__ import annotations

import os

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
    sslrootcert = os.environ.get("POSTGRES_SSLROOTCERT", "certs/global-bundle.pem")
    # connect_timeout=3: without it, a private-VPC RDS instance that's simply
    # unreachable (expected outside the VPC, ADR-009) blocks on the OS-level
    # TCP timeout (60s+) instead of failing fast into the callers' degrade path.
    return create_engine(
        _to_sqlalchemy_dsn(dsn),
        connect_args={"sslmode": "verify-full", "sslrootcert": sslrootcert, "connect_timeout": 3},
        pool_pre_ping=True,
    )


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
