"""Postgres-backed user accounts and login sessions (DB-backed opaque
session cookie, not JWT -- mirrors Node's express-session +
connect-pg-simple). Same engine/ORM base and Core-style access pattern as
rag/session_store.py and backend/services/prediction_log.py.

Unlike those two modules, functions here do NOT degrade gracefully on a
SQLAlchemyError -- they back chat history / analytics, both optional
conveniences an unreachable Postgres must not break. Auth is not optional:
letting a DB error surface as a real 500 is correct here; silently treating
it as "invalid credentials" or "not logged in" would be a security bug.
"""
from __future__ import annotations

import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import Cookie
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, select
from sqlalchemy.exc import IntegrityError

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from db import Base, get_connection, get_engine  # noqa: E402

from backend.errors import DomainError  # noqa: E402
from backend.schemas import ErrorCode  # noqa: E402

SESSION_COOKIE_NAME = "session_token"
DEFAULT_SESSION_TTL_DAYS = 30
_BCRYPT_ROUNDS = 12


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    # Deliberately not named "sessions" -- this codebase already uses
    # session_id for the chat-thread concept (messages.session_id). This
    # table is the login session; user_id is what links the two.
    __tablename__ = "auth_sessions"

    session_token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


def init_db(conninfo: str | None = None) -> None:
    engine = get_engine(conninfo)
    User.__table__.create(engine, checkfirst=True)
    AuthSession.__table__.create(engine, checkfirst=True)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_user(email: str, password: str, conninfo: str | None = None) -> dict:
    init_db(conninfo)
    table = User.__table__
    try:
        with get_engine(conninfo).begin() as conn:
            row = conn.execute(
                table.insert().values(email=email, hashed_password=hash_password(password)).returning(
                    table.c.id, table.c.email, table.c.created_at
                )
            ).mappings().one()
    except IntegrityError as exc:
        raise DomainError(ErrorCode.AUTH_EMAIL_TAKEN, f"Email '{email}' is already registered", 409) from exc
    return dict(row)


def authenticate_user(email: str, password: str, conninfo: str | None = None) -> dict | None:
    init_db(conninfo)
    table = User.__table__
    with get_connection(conninfo) as conn:
        row = conn.execute(select(table).where(table.c.email == email)).mappings().first()
    if row is None or not verify_password(password, row["hashed_password"]):
        return None
    return dict(row)


def create_session(user_id: int, ttl_days: int = DEFAULT_SESSION_TTL_DAYS, conninfo: str | None = None) -> str:
    init_db(conninfo)
    table = AuthSession.__table__
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    with get_engine(conninfo).begin() as conn:
        conn.execute(table.insert().values(session_token=session_token, user_id=user_id, expires_at=expires_at))
    return session_token


def get_user_by_session(session_token: str, conninfo: str | None = None) -> dict | None:
    init_db(conninfo)
    sessions = AuthSession.__table__
    users = User.__table__
    with get_connection(conninfo) as conn:
        row = conn.execute(
            select(users.c.id, users.c.email, users.c.created_at)
            .join(sessions, sessions.c.user_id == users.c.id)
            .where(sessions.c.session_token == session_token, sessions.c.expires_at > func.now())
        ).mappings().first()
    return dict(row) if row is not None else None


def delete_session(session_token: str, conninfo: str | None = None) -> None:
    init_db(conninfo)
    table = AuthSession.__table__
    with get_engine(conninfo).begin() as conn:
        conn.execute(table.delete().where(table.c.session_token == session_token))


def get_current_user(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    # A SQLAlchemyError here (Postgres unreachable) is deliberately NOT
    # caught -- it propagates to a real 500, per this module's docstring.
    # A missing/invalid/expired session is the only case that means
    # "not authenticated".
    if session_token is None:
        raise DomainError(ErrorCode.AUTH_NOT_AUTHENTICATED, "Not authenticated", 401)
    user = get_user_by_session(session_token)
    if user is None:
        raise DomainError(ErrorCode.AUTH_NOT_AUTHENTICATED, "Session invalid or expired", 401)
    return user
