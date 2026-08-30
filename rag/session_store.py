"""Postgres-backed conversation history store (FR-7), migrated off SQLite
per ADR-009's RDS operational store, and off raw psycopg onto SQLAlchemy.

DuckDB is single-writer and already handles analytical warehouse queries.
Session history relies on frequent small inserts from potentially multiple
backend instances, so a shared Postgres connection replaces the
per-instance SQLite file (ADR-004, SPEC-008 FR-7).

Every public function below degrades to a no-op/empty result on a
`SQLAlchemyError` instead of raising. Originally guarded against RDS being
deliberately not publicly accessible (ADR-009, private VPC); migrated to
Neon 2026-08-28 (publicly reachable, no VPC), but the degrade-gracefully
contract stays -- any transient network/DB issue should still be a
convenience-feature miss, not a request failure. Conversation history is a
convenience feature; before this guard, `answer_stream()` calling `save_message()`
before generating any answer meant one unreachable Postgres instance took
down the entire chat feature for every question, in every city (found via
/debug 2026-08-13 -- the raw connection error was also leaking to the
frontend through chat.py's WS handler, a second, related bug fixed there).
"""
from __future__ import annotations  # noqa: I001

import logging
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Table, Text, func, select
from sqlalchemy.exc import SQLAlchemyError

from db import Base, get_connection, get_engine

logger = logging.getLogger(__name__)

TABLE_NAME = "messages"
_TITLE_MAX_LEN = 60


class Message(Base):
    __tablename__ = TABLE_NAME

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, index=True)  # nullable: rows predate auth
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    route = Column(String)
    sql = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


def _table_for(table_name: str) -> Table:
    # table_name is only ever overridden by tests, to get an isolated table
    # per run against the one shared RDS instance (no local Postgres fixture
    # in this repo, ADR-009) -- production always uses the default TABLE_NAME.
    if table_name in Base.metadata.tables:
        return Base.metadata.tables[table_name]
    return Message.__table__.to_metadata(Base.metadata, name=table_name)


def init_db(conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    engine = get_engine(conninfo)
    table = _table_for(table_name)
    table.create(engine, checkfirst=True)
    # Additive migration: tables created before user_id existed keep working.
    with engine.begin() as conn:
        conn.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS user_id INTEGER')


def save_message(
    session_id: str,
    role: str,
    content: str,
    route: str | None = None,
    sql: str | None = None,
    user_id: int | None = None,
    conninfo: str | None = None,
    table_name: str = TABLE_NAME,
) -> None:
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        with get_engine(conninfo).begin() as conn:
            conn.execute(table.insert().values(
                session_id=session_id, role=role, content=content, route=route, sql=sql, user_id=user_id,
            ))
    except SQLAlchemyError as exc:
        logger.warning("session_store.save_message degraded (session history not persisted): %s", exc)


def session_exists(
    session_id: str, user_id: int | None = None, conninfo: str | None = None, table_name: str = TABLE_NAME
) -> bool:
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        with get_connection(conninfo) as conn:
            cond = table.c.session_id == session_id
            if user_id is not None:
                cond = cond & (table.c.user_id == user_id)
            row = conn.execute(select(table.c.id).where(cond).limit(1)).first()
            return row is not None
    except SQLAlchemyError as exc:
        logger.warning("session_store.session_exists degraded (treating as not found): %s", exc)
        return False


def get_session_history(
    session_id: str, user_id: int | None = None, conninfo: str | None = None, table_name: str = TABLE_NAME
) -> list[dict[str, Any]]:
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        with get_connection(conninfo) as conn:
            cols = [table.c.role, table.c.content, table.c.route, table.c.sql, table.c.timestamp]
            cond = table.c.session_id == session_id
            if user_id is not None:
                cond = cond & (table.c.user_id == user_id)
            rows = conn.execute(select(*cols).where(cond).order_by(table.c.id.asc())).mappings()
            result = []
            for row in rows:
                row = dict(row)
                row["timestamp"] = row["timestamp"].isoformat()
                result.append(row)
            return result
    except SQLAlchemyError as exc:
        logger.warning("session_store.get_session_history degraded (returning empty): %s", exc)
        return []


def list_sessions(
    user_id: int, limit: int = 50, conninfo: str | None = None, table_name: str = TABLE_NAME
) -> list[dict[str, Any]]:
    """Non-empty sessions for a user, most recently active first -- the
    history sidebar list (a session with zero messages never appears here;
    see backend/services/chat_session_service.py for that state)."""
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        with get_connection(conninfo) as conn:
            summaries = conn.execute(
                select(
                    table.c.session_id,
                    func.max(table.c.timestamp).label("last_activity"),
                    func.count().label("message_count"),
                )
                .where(table.c.user_id == user_id)
                .group_by(table.c.session_id)
                .order_by(func.max(table.c.timestamp).desc())
                .limit(limit)
            ).mappings().all()
            session_ids = [row["session_id"] for row in summaries]
            if not session_ids:
                return []
            first_messages = conn.execute(
                select(table.c.session_id, table.c.content)
                .where(table.c.session_id.in_(session_ids), table.c.role == "user")
                .order_by(table.c.id.asc())
            ).mappings()
            titles: dict[str, str] = {}
            for row in first_messages:
                titles.setdefault(row["session_id"], row["content"])

            result = []
            for row in summaries:
                title = titles.get(row["session_id"], "").strip()
                if len(title) > _TITLE_MAX_LEN:
                    title = title[:_TITLE_MAX_LEN].rstrip() + "..."
                result.append({
                    "session_id": row["session_id"],
                    "title": title or None,
                    "last_activity": row["last_activity"].isoformat(),
                    "message_count": row["message_count"],
                })
            return result
    except SQLAlchemyError as exc:
        logger.warning("session_store.list_sessions degraded (returning empty): %s", exc)
        return []


def delete_session(
    session_id: str, user_id: int | None = None, conninfo: str | None = None, table_name: str = TABLE_NAME
) -> bool:
    """Deletes all messages for a session. Returns whether anything was
    deleted -- False means the session didn't exist or wasn't owned by
    user_id, which callers should treat as 404."""
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        cond = table.c.session_id == session_id
        if user_id is not None:
            cond = cond & (table.c.user_id == user_id)
        with get_engine(conninfo).begin() as conn:
            result = conn.execute(table.delete().where(cond))
            return result.rowcount > 0
    except SQLAlchemyError as exc:
        logger.warning("session_store.delete_session degraded (nothing deleted): %s", exc)
        return False
