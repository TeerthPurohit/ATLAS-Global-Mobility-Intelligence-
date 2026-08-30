"""Service layer wrapping the RAG pipeline and conversation session history
(FR-6, FR-8), and the chat-tier dispatch point.

The served city is `full_rag`: real SQL plus vector-retrieval synthesis. It
has both a warehouse and an insight corpus, so `sql_only` is currently
unreachable -- `get_chat_tier()` still computes the tier from a real
infrastructure fact rather than asserting it, so a corpus that goes missing
degrades to SQL-grounded answers instead of silently returning nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Generator  # noqa: UP035

from loguru import logger

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import rag_pipeline  # noqa: E402
import session_store  # noqa: E402
from nl_to_sql.nyc_schema import NYC_SCHEMA  # noqa: E402

from backend.registry import cities as cities_registry  # noqa: E402

_PUBLIC_ROUTES = frozenset({"numeric", "explanatory"})


def _public_route(route: str) -> str:
    """Map every internal route label onto the public ChatRoute contract
    (numeric | explanatory)."""
    return route if route in _PUBLIC_ROUTES else "explanatory"


def answer_question(question: str, session_id: str | None = None, user_id: int | None = None) -> dict[str, Any]:
    tier = cities_registry.get_chat_tier()
    logger.info("rag_service.answer_question step=routed tier={}", tier)
    res = rag_pipeline.answer(
        question=question, session_id=session_id,
        db_path=rag_pipeline.DEFAULT_DB_PATH,
        schema=NYC_SCHEMA,
        allow_explanatory=(tier == "full_rag"),
        collection=rag_pipeline.DEFAULT_COLLECTION,
        user_id=user_id,
    )
    res["route"] = _public_route(res["route"])
    return res


def stream_answer(
    question: str, session_id: str | None = None, user_id: int | None = None
) -> Generator[dict[str, Any], None, None]:
    """Streaming twin of answer_question -- same tier dispatch, so WS
    /chat/stream and POST /chat behave identically.

    A "done" frame's payload carries the answer-family fields; the router
    (chat.py) is responsible for echoing any request context onto it.
    """
    if cities_registry.get_chat_tier() == "sql_only":
        # A warehouse but no insight corpus: answer_stream's explanatory
        # branch would never emit a "done" frame, so stream the same
        # SQL-grounded answer POST /chat returns instead.
        res = rag_pipeline.answer(
            question=question, session_id=session_id,
            db_path=rag_pipeline.DEFAULT_DB_PATH,
            schema=NYC_SCHEMA,
            allow_explanatory=False,
            user_id=user_id,
        )
        res["route"] = _public_route(res["route"])
        yield {"type": "chunk", "text": res["answer"]}
        yield {"type": "done", "payload": res}
        return
    yield from rag_pipeline.answer_stream(
        question=question, session_id=session_id,
        collection=rag_pipeline.DEFAULT_COLLECTION,
        user_id=user_id,
    )


def get_history(session_id: str, user_id: int | None = None) -> list[dict[str, Any]] | None:
    if not session_store.session_exists(session_id, user_id=user_id):
        return None
    return session_store.get_session_history(session_id, user_id=user_id)


def list_sessions(user_id: int) -> list[dict[str, Any]]:
    return session_store.list_sessions(user_id=user_id)


def delete_history(session_id: str, user_id: int) -> bool:
    return session_store.delete_session(session_id, user_id=user_id)
