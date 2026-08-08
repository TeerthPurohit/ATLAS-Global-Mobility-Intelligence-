"""Service layer wrapping RAG pipeline and conversation session history
(FR-6, FR-8) -- now the actual chat-tier dispatch point (SPEC-013 FR-11):
`full_rag` (NYC, real SQL + vector-retrieval synthesis), `sql_only`
(London, real SQL against its own warehouse, honest refusal for anything
needing insight-doc prose), `context_only` (any other resolvable city --
never a flat refusal, an LLM-narrated answer grounded in real
geography/weather/holiday/estimate data instead).
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Generator

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import rag_pipeline  # noqa: E402
import session_store  # noqa: E402
from llm_client import chat_completion  # noqa: E402
from nl_to_sql.london_schema import LONDON_SCHEMA  # noqa: E402
from nl_to_sql.nyc_schema import NYC_SCHEMA  # noqa: E402

from backend.registry import cities as cities_registry  # noqa: E402
from backend.services import context_orchestrator, estimation_service, global_geography_service  # noqa: E402

_CITY_DB_PATH = {"london": Path(__file__).resolve().parents[2] / "data" / "warehouse" / "london_cycles.duckdb"}
_CITY_SCHEMA = {"london": LONDON_SCHEMA}

_CONTEXT_ONLY_SYSTEM_PROMPT = """You are a mobility-data assistant for {city_name}. \
You may ONLY state facts that literally appear in the JSON context below -- \
never invent, calculate, or infer a number that isn't already present in it. \
If part of the user's question needs data not present in this context \
(e.g. a historical trend, a specific past trip, anything requiring observed \
trip-level history), say plainly that this specific city doesn't have that \
kind of data available yet -- but still answer whatever part of the \
question the context below actually covers. Never refuse the whole question \
just because one part of it is unanswerable.

Context (real data, from this platform's own geography/weather/holiday/estimate services):
{context}
"""


def _answer_context_only(question: str, city_id: str) -> dict[str, Any]:
    ctx = context_orchestrator.get_city_context(city_id)
    profile = global_geography_service.get_city_profile(city_id)
    fare_estimate = None
    if profile and profile.get("country_code"):
        fare_estimate = estimation_service.estimate_fare_per_mile(profile["country_code"])

    context_payload = {
        "city": ctx.get("city_name"),
        **ctx.get("context", {}),
    }
    if fare_estimate is not None:
        context_payload["fare_per_mile_estimate"] = {
            "status": fare_estimate.basis, "value": fare_estimate.value,
            "unit": fare_estimate.unit, "reason": fare_estimate.reason,
        }

    import json

    try:
        resp = chat_completion(
            model="gpt-5.4-nano",
            messages=[
                {"role": "system", "content": _CONTEXT_ONLY_SYSTEM_PROMPT.format(
                    city_name=ctx.get("city_name", city_id), context=json.dumps(context_payload, default=str, indent=2),
                )},
                {"role": "user", "content": question},
            ],
            temperature=0.2,
            max_completion_tokens=300,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 -- LLM failure still gives a real, non-fabricated answer
        text = (
            f"Live narration isn't available right now ({exc}), but here's what's real for {ctx.get('city_name', city_id)}: "
            + json.dumps(context_payload, default=str)
        )

    return {
        "answer": text, "route": "context_grounded", "sql": None,
        "session_id": str(uuid.uuid4()), "sources": ["context_orchestrator"],
    }


def answer_question(question: str, session_id: str | None = None, city_id: str = "nyc") -> dict[str, Any]:
    tier = cities_registry.get_chat_tier(city_id)
    if tier == "context_only":
        res = _answer_context_only(question, city_id)
        res["session_id"] = session_id or res["session_id"]
        return res
    return rag_pipeline.answer(
        question=question, session_id=session_id,
        db_path=_CITY_DB_PATH.get(city_id, rag_pipeline.DEFAULT_DB_PATH),
        schema=_CITY_SCHEMA.get(city_id, NYC_SCHEMA),
        allow_explanatory=(tier == "full_rag"),
    )


def stream_answer(question: str, session_id: str | None = None) -> Generator[dict[str, Any], None, None]:
    yield from rag_pipeline.answer_stream(question=question, session_id=session_id)


def get_history(session_id: str) -> list[dict[str, Any]] | None:
    if not session_store.session_exists(session_id):
        return None
    return session_store.get_session_history(session_id)
