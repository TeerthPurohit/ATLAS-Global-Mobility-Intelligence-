"""Service layer wrapping the RAG pipeline and conversation session history
(FR-6, FR-8), and the chat-tier dispatch point.

NYC is `full_rag`: real SQL plus vector-retrieval synthesis. It is the only
city served (ADR-012), and it has both a warehouse and an insight corpus, so
the other tiers are currently unreachable -- `get_chat_tier` still computes
them from real infrastructure facts, so a future city routes correctly the
moment it is registered.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Generator

from loguru import logger

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import rag_pipeline  # noqa: E402
import session_store  # noqa: E402
from nl_to_sql.nyc_schema import NYC_SCHEMA  # noqa: E402

from backend.registry import cities as cities_registry  # noqa: E402

# Per-city overrides. Empty: nyc is the default everywhere --
# rag_pipeline.answer()/answer_stream() fall back to the nyc warehouse,
# NYC_SCHEMA, and the nyc collection (embeddings.build_vector_store.COLLECTION)
# when a city has no entry here. A second city adds one row to each.
_CITY_DB_PATH: dict[str, Path] = {}
_CITY_SCHEMA: dict[str, object] = {}
_CITY_INSIGHT_COLLECTION: dict[str, str] = {}

_PUBLIC_ROUTES = frozenset({"numeric", "explanatory"})


def _public_route(route: str) -> str:
    """Map every internal route label onto the public ChatRoute contract
    (numeric | explanatory)."""
    return route if route in _PUBLIC_ROUTES else "explanatory"


def answer_question(question: str, session_id: str | None = None, city_id: str = "nyc") -> dict[str, Any]:
    tier = cities_registry.get_chat_tier(city_id)
    logger.info("rag_service.answer_question step=routed city_id={} tier={}", city_id, tier)
    res = rag_pipeline.answer(
        question=question, session_id=session_id,
        db_path=_CITY_DB_PATH.get(city_id, rag_pipeline.DEFAULT_DB_PATH),
        schema=_CITY_SCHEMA.get(city_id, NYC_SCHEMA),
        allow_explanatory=(tier == "full_rag"),
        collection=_CITY_INSIGHT_COLLECTION.get(city_id, rag_pipeline.DEFAULT_COLLECTION),
    )
    res["route"] = _public_route(res["route"])
    return res


def stream_answer(question: str, session_id: str | None = None, city_id: str = "nyc") -> Generator[dict[str, Any], None, None]:
    """Streaming twin of answer_question -- same city_id routing, so WS
    /chat/stream and POST /chat behave identically per city tier. Backward
    compatible: a caller that omits city_id keeps the original NYC default.

    A "done" frame's payload carries the answer-family fields; the router
    (chat.py) is responsible for echoing city_id/area_id onto it.
    """
    tier = cities_registry.get_chat_tier(city_id)
    if tier == "sql_only":
        # A warehouse but no insight corpus: answer_stream's explanatory
        # branch would never emit a "done" frame, so stream the same
        # SQL-grounded answer POST /chat returns instead.
        res = rag_pipeline.answer(
            question=question, session_id=session_id,
            db_path=_CITY_DB_PATH.get(city_id, rag_pipeline.DEFAULT_DB_PATH),
            schema=_CITY_SCHEMA.get(city_id, NYC_SCHEMA),
            allow_explanatory=False,
        )
        res["route"] = _public_route(res["route"])
        yield {"type": "chunk", "text": res["answer"]}
        yield {"type": "done", "payload": res}
        return
    yield from rag_pipeline.answer_stream(
        question=question, session_id=session_id,
        collection=_CITY_INSIGHT_COLLECTION.get(city_id, rag_pipeline.DEFAULT_COLLECTION),
    )


def get_history(session_id: str) -> list[dict[str, Any]] | None:
    if not session_store.session_exists(session_id):
        return None
    return session_store.get_session_history(session_id)
