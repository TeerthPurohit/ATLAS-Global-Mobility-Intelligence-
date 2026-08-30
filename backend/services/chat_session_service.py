"""Postgres-backed chat session bookkeeping (backend/routers/chat.py's
POST/GET/DELETE /chat/sessions). Same engine/Base/Core-style access pattern
as backend/services/auth_service.py and rag/session_store.py.

The `messages` table (rag/session_store.py) is the source of truth for a
session's *content* -- a session with zero messages leaves no row there at
all, so it can't represent a freshly-created "New Chat" session waiting for
its first question. This table exists solely to give an empty session a
place to live so it can be found and reused (ChatGPT/Claude's "New Chat"
doesn't pile up empty conversations if you click it twice) -- nothing else
in the chat pipeline (rag_pipeline.py, session_store.py, rag_service.py)
reads or writes it.

Degrades gracefully on SQLAlchemyError, like session_store.py -- session
bookkeeping is a convenience feature, not a security boundary like auth.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, select
from sqlalchemy.exc import SQLAlchemyError

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from db import Base, get_connection, get_engine  # noqa: E402
from session_store import Message  # noqa: E402

TABLE_NAME = "chat_sessions"


class ChatSession(Base):
    __tablename__ = TABLE_NAME

    session_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db(conninfo: str | None = None) -> None:
    ChatSession.__table__.create(get_engine(conninfo), checkfirst=True)


def create_or_reuse_session(user_id: int, conninfo: str | None = None) -> str:
    """Reuses the user's most recently created still-empty session (no rows
    in `messages` yet) if one exists, otherwise mints a new one."""
    try:
        init_db(conninfo)
        sessions = ChatSession.__table__
        messages = Message.__table__
        with get_connection(conninfo) as conn:
            existing = conn.execute(
                select(sessions.c.session_id)
                .select_from(sessions.outerjoin(messages, messages.c.session_id == sessions.c.session_id))
                .where(sessions.c.user_id == user_id, messages.c.id.is_(None))
                .order_by(sessions.c.created_at.desc())
                .limit(1)
            ).scalar()
        if existing is not None:
            return existing

        new_session_id = str(uuid.uuid4())
        with get_engine(conninfo).begin() as conn:
            conn.execute(sessions.insert().values(session_id=new_session_id, user_id=user_id))
        return new_session_id
    except SQLAlchemyError as exc:
        logger.warning("chat_session_service.create_or_reuse_session degraded (minting an untracked id): {}", exc)
        return str(uuid.uuid4())


def delete_session_row(session_id: str, user_id: int, conninfo: str | None = None) -> bool:
    """Deletes the bookkeeping row for an empty session (one with no
    messages yet). Ownership-scoped like session_store.delete_session --
    returns False if the row didn't exist or belonged to another user."""
    try:
        init_db(conninfo)
        table = ChatSession.__table__
        with get_engine(conninfo).begin() as conn:
            result = conn.execute(
                table.delete().where(table.c.session_id == session_id, table.c.user_id == user_id)
            )
            return result.rowcount > 0
    except SQLAlchemyError as exc:
        logger.warning("chat_session_service.delete_session_row degraded (bookkeeping row may remain): {}", exc)
        return False
