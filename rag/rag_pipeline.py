"""Ties router -> dispatch -> grounded answer together (FR-5, ADR-004).

Numeric path: `router/query_classifier.py` -> `nl_to_sql/sql_agent.py`
(real SQL, executed, result formatted directly -- no LLM paraphrase step at
all, since the safest and simplest way to avoid an LLM inventing a number
here is to never ask it to touch the number in the first place).

Explanatory path: `router/query_classifier.py` -> `embeddings/
build_vector_store.py` cosine-similarity retrieval over `insight_generation`
docs, then one short LLM synthesis pass that is only allowed to reuse
numbers already present in the retrieved doc text -- checked with the same
`validate_grounding()` used when those docs were generated. If synthesis
ever introduces an ungrounded number, the retrieved doc's own (already-
grounded) text is returned verbatim instead of the LLM's rewrite.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Generator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DEFAULT_DB_PATH, OPENAI_MODEL  # noqa: E402
from embeddings.build_vector_store import COLLECTION as DEFAULT_COLLECTION  # noqa: E402
from embeddings.build_vector_store import search as vector_search  # noqa: E402
from insight_generation.generate_insight_docs import extract_numbers, validate_grounding  # noqa: E402
from llm_client import chat_completion  # noqa: E402
from nl_to_sql import sql_agent  # noqa: E402
from nl_to_sql.nyc_schema import NYC_SCHEMA  # noqa: E402
from nl_to_sql.query_plan import CityMobilitySchema  # noqa: E402
from router.query_classifier import EXPLANATORY, NUMERIC, classify  # noqa: E402
import semantic_cache  # noqa: E402
import session_store  # noqa: E402

SYNTHESIS_SYSTEM_PROMPT = """Answer the user's question in 2-4 plain-language \
sentences using ONLY facts and numbers that literally appear in the \
retrieved context below. Do not calculate, round, infer, or add any number, \
statistic, or comparison that isn't already stated in the context. If the \
context doesn't fully answer the question, say plainly what it does cover \
and note the rest isn't available -- never guess.

Retrieved context:
{context}
"""


_MONEY_COLS = ("fare", "amount", "price", "cost", "tip", "toll", "revenue")


def _format_label(col: str) -> str:
    return col.replace("_", " ").title()


def _format_value(col: str, val) -> str:
    if isinstance(val, bool) or val is None:
        return str(val)
    if isinstance(val, (int, float)):
        is_money = any(m in col.lower() for m in _MONEY_COLS)
        if is_money or isinstance(val, float):
            return f"${val:,.2f}" if is_money else f"{val:,.2f}"
        return f"{val:,}"
    return str(val)


def _format_numeric_answer(result: dict) -> str:
    rows = result["rows"]
    if not rows:
        return "The query ran but returned no matching rows."

    if len(rows) == 1:
        row = rows[0]
        lines = [f"- {_format_label(col)}: {_format_value(col, val)}" for col, val in row.items()]
        return "Based on the marts:\n" + "\n".join(lines)

    shown = rows[:10]
    lines = [
        ", ".join(f"{_format_label(col)}: {_format_value(col, val)}" for col, val in row.items())
        for row in shown
    ]
    suffix = f"\n\n(showing first 10 of {len(rows)} rows)" if len(rows) > 10 else ""
    return "Based on the marts:\n" + "\n".join(f"- {line}" for line in lines) + suffix


def _answer_numeric(question: str, db_path: Path = DEFAULT_DB_PATH, schema: CityMobilitySchema = NYC_SCHEMA) -> dict:
    result = sql_agent.answer(question, db_path=db_path, schema=schema)
    return {
        "question": question,
        "route": NUMERIC,
        "answer": _format_numeric_answer(result),
        "sql": result["sql"],
        "rows": result["rows"],
        "sources": None,
    }


def _hit_label(h: dict) -> str:
    """NYC hits carry zone_name/borough; a station-based city would carry
    station_name only -- one location label either way, not a city-specific
    formatter per caller."""
    if h.get("zone_name"):
        return f"{h['zone_name']}, {h.get('borough', '')}".rstrip(", ")
    return h.get("station_name", "unknown location")


def _hit_source(h: dict) -> dict:
    label_key = "zone_name" if h.get("zone_name") else "station_name"
    source = {label_key: h.get(label_key), "score": h["score"]}
    if h.get("borough"):
        source["borough"] = h["borough"]
    return source


def _synthesize_explanatory(question: str, hits: list[dict]) -> str:
    context = "\n\n".join(f"[{_hit_label(h)}] {h['doc_text']}" for h in hits)
    allowed = set(extract_numbers(context))

    try:
        resp = chat_completion(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT.format(context=context)},
                {"role": "user", "content": question},
            ],
            temperature=0.2,
            max_completion_tokens=250,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 -- any LLM/network failure falls back to raw retrieval
        print(f"[warn] explanatory synthesis failed ({exc}); returning retrieved doc verbatim", file=sys.stderr)
        return hits[0]["doc_text"]

    if not text or not validate_grounding(text, allowed):
        print("[warn] synthesis introduced an ungrounded number; returning retrieved doc verbatim", file=sys.stderr)
        return hits[0]["doc_text"]
    return text


def _answer_explanatory(question: str, k: int = 3, collection: str = DEFAULT_COLLECTION) -> dict:
    cached = semantic_cache.get(question, namespace=collection)
    if cached is not None:
        return cached

    hits = vector_search(question, k=k, collection=collection)
    if not hits:
        return {
            "question": question,
            "route": EXPLANATORY,
            "answer": "No insight documents are available yet for this question -- not yet measured.",
            "sql": None,
            "rows": None,
            "sources": [],
        }
    answer_text = _synthesize_explanatory(question, hits)
    result = {
        "question": question,
        "route": EXPLANATORY,
        "answer": answer_text,
        "sql": None,
        "rows": None,
        "sources": [_hit_source(h) for h in hits],
    }
    semantic_cache.put(question, namespace=collection, result=result)
    return result


def answer(
    question: str, session_id: str | None = None, db_path: Path = DEFAULT_DB_PATH,
    schema: CityMobilitySchema = NYC_SCHEMA, allow_explanatory: bool = True, collection: str = DEFAULT_COLLECTION,
) -> dict:
    active_session_id = session_id or str(uuid.uuid4())
    route = classify(question)
    if route == NUMERIC:
        res = _answer_numeric(question, db_path=db_path, schema=schema)
    elif allow_explanatory:
        res = _answer_explanatory(question, collection=collection)
    else:
        res = {
            "question": question, "route": EXPLANATORY,
            "answer": f"No insight documents exist for {schema.name} yet -- ask a specific numeric question about demand instead.",
            "sql": None, "rows": None, "sources": [],
        }

    res["session_id"] = active_session_id
    session_store.save_message(active_session_id, "user", question)
    session_store.save_message(active_session_id, "assistant", res["answer"], route=res["route"], sql=res.get("sql"))
    return res


def answer_stream(
    question: str, session_id: str | None = None, collection: str = DEFAULT_COLLECTION,
) -> Generator[dict, None, None]:
    """Streaming generator variant yielding tokens/chunks and final complete payload."""
    active_session_id = session_id or str(uuid.uuid4())
    route = classify(question)

    session_store.save_message(active_session_id, "user", question)

    if route == NUMERIC:
        res = _answer_numeric(question)
        res["session_id"] = active_session_id
        session_store.save_message(active_session_id, "assistant", res["answer"], route=NUMERIC, sql=res.get("sql"))
        yield {"type": "chunk", "text": res["answer"]}
        yield {"type": "done", "payload": res}
        return

    # Explanatory route with streaming LLM synthesis
    hits = vector_search(question, k=3, collection=collection)
    if not hits:
        fallback_ans = "No insight documents are available yet for this question -- not yet measured."
        payload = {
            "question": question,
            "route": EXPLANATORY,
            "answer": fallback_ans,
            "sql": None,
            "rows": None,
            "sources": [],
            "session_id": active_session_id,
        }
        session_store.save_message(active_session_id, "assistant", fallback_ans, route=EXPLANATORY)
        yield {"type": "chunk", "text": fallback_ans}
        yield {"type": "done", "payload": payload}
        return

    context = "\n\n".join(f"[{_hit_label(h)}] {h['doc_text']}" for h in hits)
    allowed = set(extract_numbers(context))
    accumulated_text = ""

    try:
        stream = chat_completion(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT.format(context=context)},
                {"role": "user", "content": question},
            ],
            temperature=0.2,
            max_completion_tokens=250,
            stream=True,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                accumulated_text += token
                yield {"type": "chunk", "text": token}
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] streaming synthesis failed ({exc}); falling back to retrieved doc", file=sys.stderr)
        accumulated_text = hits[0]["doc_text"]
        yield {"type": "chunk", "text": accumulated_text}

    final_text = accumulated_text.strip()
    if not final_text or not validate_grounding(final_text, allowed):
        print("[warn] synthesis introduced an ungrounded number; returning retrieved doc verbatim", file=sys.stderr)
        final_text = hits[0]["doc_text"]

    payload = {
        "question": question,
        "route": EXPLANATORY,
        "answer": final_text,
        "sql": None,
        "rows": None,
        "sources": [_hit_source(h) for h in hits],
        "session_id": active_session_id,
    }
    session_store.save_message(active_session_id, "assistant", final_text, route=EXPLANATORY)
    yield {"type": "done", "payload": payload}


def demo() -> None:
    for question in [
        "What is the average fare for trips picked up in JFK Airport?",
        "Why is JFK Airport such an important hub in the network?",
    ]:
        result = answer(question)
        print(f"\nQ: {question}\nroute: {result['route']}\nsession_id: {result['session_id']}")
        if result["sql"]:
            print(f"SQL: {result['sql']}")
        print(f"A: {result['answer']}")
        assert result["answer"], "must always produce some answer text"


if __name__ == "__main__":
    demo()
