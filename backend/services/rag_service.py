"""Service layer wrapping RAG pipeline and conversation session history
(FR-6, FR-8) -- now the actual chat-tier dispatch point (SPEC-013 FR-11):
`full_rag` (NYC, real SQL + vector-retrieval synthesis) and `sql_only`
(a city with its own warehouse but no insight-doc corpus -- real SQL, honest
refusal for anything needing prose). The `context_only` tier went away with
the global layer (ADR-011): every city this repo serves now has a warehouse.
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
from nl_to_sql.london_schema import LONDON_SCHEMA  # noqa: E402
from nl_to_sql.nyc_schema import NYC_SCHEMA  # noqa: E402

from backend.registry import cities as cities_registry  # noqa: E402

_CITY_DB_PATH = {"london": Path(__file__).resolve().parents[2] / "data" / "warehouse" / "london_cycles.duckdb"}
_CITY_SCHEMA = {"london": LONDON_SCHEMA}
# nyc omitted -- rag_pipeline.answer()/answer_stream() default to the nyc
# collection (embeddings.build_vector_store.COLLECTION) when not overridden.
_CITY_INSIGHT_COLLECTION = {"london": "insight_docs_london"}

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
        # London has no insight-doc corpus, so answer_stream's explanatory
        # branch would never emit a "done" frame -- stream the same
        # SQL-grounded answer POST /chat returns instead.
        res = rag_pipeline.answer(
            question=question, session_id=session_id,
            db_path=_CITY_DB_PATH[city_id], schema=_CITY_SCHEMA[city_id],
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
