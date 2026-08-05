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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OPENAI_MODEL  # noqa: E402
from embeddings.build_vector_store import search as vector_search  # noqa: E402
from insight_generation.generate_insight_docs import extract_numbers, validate_grounding  # noqa: E402
from nl_to_sql import sql_agent  # noqa: E402
from router.query_classifier import EXPLANATORY, NUMERIC, classify  # noqa: E402

SYNTHESIS_SYSTEM_PROMPT = """Answer the user's question in 2-4 plain-language \
sentences using ONLY facts and numbers that literally appear in the \
retrieved context below. Do not calculate, round, infer, or add any number, \
statistic, or comparison that isn't already stated in the context. If the \
context doesn't fully answer the question, say plainly what it does cover \
and note the rest isn't available -- never guess.

Retrieved context:
{context}
"""


def _format_numeric_answer(result: dict) -> str:
    rows = result["rows"]
    if not rows:
        return "The query ran but returned no matching rows."
    if len(rows) == 1:
        row = rows[0]
        parts = [f"{col.replace('_', ' ')} = {val}" for col, val in row.items()]
        return "Based on the marts: " + "; ".join(parts) + "."

    shown = rows[:10]
    lines = [", ".join(f"{col}={val}" for col, val in row.items()) for row in shown]
    suffix = f" (showing first 10 of {len(rows)} rows)" if len(rows) > 10 else ""
    return "Based on the marts:\n" + "\n".join(f"- {line}" for line in lines) + suffix


def _answer_numeric(question: str) -> dict:
    result = sql_agent.answer(question)
    return {
        "question": question,
        "route": NUMERIC,
        "answer": _format_numeric_answer(result),
        "sql": result["sql"],
        "rows": result["rows"],
        "sources": None,
    }


def _synthesize_explanatory(question: str, hits: list[dict]) -> str:
    context = "\n\n".join(f"[{h['zone_name']}, {h['borough']}] {h['doc_text']}" for h in hits)
    allowed = set(extract_numbers(context))

    try:
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
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


def _answer_explanatory(question: str, k: int = 3) -> dict:
    hits = vector_search(question, k=k)
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
    return {
        "question": question,
        "route": EXPLANATORY,
        "answer": answer_text,
        "sql": None,
        "rows": None,
        "sources": [{"zone_name": h["zone_name"], "borough": h["borough"], "score": h["score"]} for h in hits],
    }


def answer(question: str) -> dict:
    route = classify(question)
    if route == NUMERIC:
        return _answer_numeric(question)
    return _answer_explanatory(question)


def demo() -> None:
    for question in [
        "What is the average fare for trips picked up in JFK Airport?",
        "Why is JFK Airport such an important hub in the network?",
    ]:
        result = answer(question)
        print(f"\nQ: {question}\nroute: {result['route']}")
        if result["sql"]:
            print(f"SQL: {result['sql']}")
        print(f"A: {result['answer']}")
        assert result["answer"], "must always produce some answer text"


if __name__ == "__main__":
    demo()
