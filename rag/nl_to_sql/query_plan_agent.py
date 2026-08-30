"""NL question -> QueryPlan (fine-tuned model) -> compiled SQL -> executed
read-only result (FR-9, spec-014).

Gated behind `USE_FINETUNED_QUERY_PLAN` (default unset/off). `rag_pipeline.py`
does not import this module at all -- the live numeric-question path keeps
calling `sql_agent.answer()` exactly as today, unchanged by this file's
existence. No fine-tuned model exists yet (spec-014's FR-7 fine-tuning step
is done separately, not by this module), so `answer()` always raises today;
that's expected -- this builds the mechanism correctly for when a fine-tuned
model id is configured, it does not pretend one exists.

Reuses `sql_agent.py`'s mart allow-list and read-only-connection pattern
rather than reinventing it (FR-9): even though `query_plan_compiler.compile()`
only ever emits schema-declared table names, the executed SQL's table is
independently re-checked against `sql_agent.ALLOWED_TABLES` before running,
matching ADR-004's defense-in-depth discipline.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import DEFAULT_DB_PATH
from nyc_schema import NYC_SCHEMA
from query_plan import CityMobilitySchema, QueryPlan
from query_plan_compiler import compile as compile_plan
from sql_agent import ALLOWED_TABLES

USE_FINETUNED_QUERY_PLAN = os.environ.get("USE_FINETUNED_QUERY_PLAN", "").strip().lower() in ("1", "true", "yes")
FINETUNED_MODEL_ID = os.environ.get("QUERY_PLAN_FINETUNED_MODEL_ID", "")

_TABLE_REF_RE = re.compile(r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return text


def generate_plan(question: str, schema: CityMobilitySchema, model: str) -> QueryPlan:
    """System prompt is `schema.describe()` alone -- exactly the training
    format `training_data_gen.py` emits, since the fine-tuned model learns
    the QueryPlan JSON shape from those examples, not from a repeated
    instruction (see evaluate.py's docstring for why the base-model eval
    prompt differs from this one)."""
    # Routed through llm_client.chat_completion (same as sql_agent.generate_plan)
    # rather than OpenAI() directly -- this is what makes the local fine-tuned
    # model (spec-014 FR-7, docs/superpowers/specs/2026-08-27-local-queryplan-
    # model-design.md) actually reachable from QueryPlan generation at all.
    # Tradeoff, deliberate: chat_completion's local tier is process-wide, so
    # setting LOCAL_MODEL_BASE_URL routes *every* chat_completion() caller in
    # the repo (rag_pipeline, sql_agent) at the local model too, not just this
    # one. Accepted over a per-call opt-in flag; see evaluate_comparison.py's
    # run() for the one place that has to override it back off.
    from llm_client import chat_completion

    resp = chat_completion(
        model=model,
        messages=[
            {"role": "system", "content": schema.describe()},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_completion_tokens=300,
        trace_name="query_plan_agent.generate_plan",
        # No prompt_version: the system content is schema.describe(), a
        # dynamic per-schema dump rather than a hand-authored rag/prompts/
        # template -- nothing to version here.
    )
    text = _strip_fences(resp.choices[0].message.content or "")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return QueryPlan.from_dict(data)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(f"Model returned non-JSON QueryPlan: {text!r}") from exc
    raise ValueError(f"Model output did not match QueryPlan dict schema: {text!r}")


def answer(question: str, schema: CityMobilitySchema = NYC_SCHEMA, db_path: Path = DEFAULT_DB_PATH) -> dict:
    if not USE_FINETUNED_QUERY_PLAN:
        raise RuntimeError("query_plan_agent is disabled -- set USE_FINETUNED_QUERY_PLAN=1 to enable")
    if not FINETUNED_MODEL_ID:
        raise RuntimeError(
            "USE_FINETUNED_QUERY_PLAN is on but QUERY_PLAN_FINETUNED_MODEL_ID is unset -- no "
            "fine-tuned model has been trained yet (spec-014 FR-7, submitted/run separately)"
        )

    plan = generate_plan(question, schema, FINETUNED_MODEL_ID)
    sql = compile_plan(plan, schema)

    table_match = _TABLE_REF_RE.search(sql)
    table_name = table_match.group(1) if table_match else None
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"compiled SQL references disallowed table {table_name!r}: {sql!r}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(sql).df()
    finally:
        con.close()
    return {
        "question": question,
        "plan": plan.to_dict(),
        "sql": sql,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }


def demo() -> None:
    try:
        answer("What is the average fare for JFK Airport?")
        raise AssertionError("should have raised while USE_FINETUNED_QUERY_PLAN is unset")
    except RuntimeError as exc:
        assert "USE_FINETUNED_QUERY_PLAN" in str(exc)
    print("OK: query_plan_agent stays disabled by default (USE_FINETUNED_QUERY_PLAN unset)")


if __name__ == "__main__":
    demo()
