"""NL-to-SQL over the mart schema only (FR-3, ADR-004; restructured for
SPEC-013 FR-10).

The LLM never emits SQL text anymore. It's prompted with `nyc_schema.py`'s
`CityMobilitySchema.describe()` and asked to return ONLY a `QueryPlan` JSON
object (`query_plan.py`) -- intent/metric/filters/aggregation, no table or
column name. `query_plan_compiler.compile()` resolves every field the plan
references against `NYC_SCHEMA` and deterministically compiles it to SQL;
an unresolvable field raises rather than emitting a guessed query. The
compiled SQL is still independently re-checked by `_validate_sql()` (table
allow-list + DDL/DML keyword blocklist, unchanged) before execution --
defense in depth, not the primary guard anymore. This closes the NL-to-SQL
injection surface: no code path here concatenates LLM-authored text into a
query.

`query_plan.py`/`query_plan_compiler.py`/`nyc_schema.py` are shared with
`query_plan_agent.py`'s separate, opt-in `USE_FINETUNED_QUERY_PLAN` path
(SPEC-014) -- this module is what makes QueryPlan-based compilation the
*live*, default `/chat` behavior (SPEC-013 FR-10's actual requirement),
using today's zero-shot base model rather than a not-yet-trained fine-tune;
query_plan_agent.py's opt-in path is untouched by this change.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEFAULT_DB_PATH, OPENAI_MODEL  # noqa: E402
from nyc_schema import NYC_SCHEMA  # noqa: E402
from query_plan import CityMobilitySchema, QueryPlan  # noqa: E402
from query_plan_compiler import compile as compile_plan  # noqa: E402

ALLOWED_TABLES = {"zone_hourly_demand", "zone_fare_stats", "zone_pair_flows"}

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|export|import|"
    r"pragma|call|grant|vacuum|checkpoint|replace)\b",
    re.IGNORECASE,
)
_STARTS_SELECT = re.compile(r"^\s*(with|select)\b", re.IGNORECASE)
_CTE_NAME_RE = re.compile(r"\b(\w+)\s+as\s*\(", re.IGNORECASE)
_TABLE_REF_RE = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)

SYSTEM_PROMPT_TEMPLATE = """You are a query planner for a {city_name} mobility data \
platform. Given a user's question, respond with ONLY a JSON object matching \
this shape -- never SQL, never markdown, never an explanation:

{{"intent": "area_ranking"|"metric_lookup"|"top_n"|"comparison"|"hourly_pattern", \
"metric": "demand"|"fare"|"flow", \
"filters": {{"hour": <int or null>, "area": <string or null>, "date_range": <[string,string] or null>}}, \
"aggregation": "count"|"avg"|"sum"|"max"|"min", "group_by": <string or null>, \
"order": "asc"|"desc"|null, "limit": <int or null>}}

Only reference fields this schema actually resolves for the metric you pick:

{schema}

If the question asks for a filter a metric has no column for (e.g. an \
hour-of-day filter on a metric with no hour column), omit that filter from \
the JSON -- never invent one.
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return text


def _validate_sql(sql: str, allowed_tables: set[str] = ALLOWED_TABLES) -> None:
    """Defense-in-depth guard (ADR-004): compile_plan() only ever emits
    schema-declared table/column names, this independently re-checks the
    compiled text against a table allow-list and DDL/DML keyword blocklist
    before execution. `allowed_tables` defaults to NYC's for backward
    compatibility; other schemas pass their own metric tables."""
    if not _STARTS_SELECT.match(sql):
        raise ValueError(f"generated SQL must start with SELECT or WITH: {sql!r}")
    if ";" in sql:
        raise ValueError(f"generated SQL must be a single statement: {sql!r}")
    if _FORBIDDEN_KEYWORDS.search(sql):
        raise ValueError(f"generated SQL contains a forbidden keyword: {sql!r}")

    cte_names = {m.lower() for m in _CTE_NAME_RE.findall(sql)}
    referenced = {m.lower() for m in _TABLE_REF_RE.findall(sql)}
    allowed = {t.lower() for t in allowed_tables} | cte_names
    illegal = referenced - allowed
    if illegal:
        raise ValueError(f"generated SQL references disallowed table(s) {illegal}: {sql!r}")


def generate_plan(question: str, schema: CityMobilitySchema = NYC_SCHEMA, model: str = OPENAI_MODEL) -> QueryPlan:
    """The one place an LLM is called on the numeric-question path -- its
    entire output is a QueryPlan JSON object, never SQL text. DeepSeek is
    tried first (llm_client.py), OpenAI as fallback."""
    from llm_client import chat_completion

    resp = chat_completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(city_name=schema.name, schema=schema.describe())},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_completion_tokens=300,
    )
    text = _strip_fences(resp.choices[0].message.content or "")
    return QueryPlan.from_json(text)


def answer(
    question: str, db_path: Path = DEFAULT_DB_PATH, schema: CityMobilitySchema = NYC_SCHEMA, model: str = OPENAI_MODEL,
) -> dict:
    """Question -> QueryPlan -> deterministically compiled SQL -> real,
    read-only result -- never a value the LLM invented, and never SQL text
    the LLM wrote directly (SPEC-013 FR-10)."""
    plan = generate_plan(question, schema=schema, model=model)
    sql = compile_plan(plan, schema)
    _validate_sql(sql, {m.table for m in schema.metrics.values()})

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
    # Security guard self-check: every one of these must be rejected before
    # ever reaching a live connection (unchanged from before FR-10 -- still
    # exercised directly, since _validate_sql is still a real second layer
    # even though compile_plan() is now the primary source of the SQL text).
    bad_queries = [
        "SELECT * FROM stg_trips",
        "SELECT * FROM int_trips_enriched",
        "DROP TABLE zone_hourly_demand",
        "SELECT * FROM zone_hourly_demand; DROP TABLE zone_hourly_demand",
        "INSERT INTO zone_hourly_demand VALUES (1)",
    ]
    for q in bad_queries:
        try:
            _validate_sql(q)
            raise AssertionError(f"should have rejected: {q!r}")
        except ValueError:
            pass
    print("OK: security guard rejects raw tables / multi-statement / DDL-DML")

    good = "SELECT pickup_zone, AVG(avg_fare) AS avg_fare FROM zone_hourly_demand " \
           "WHERE pickup_zone = 'JFK Airport' GROUP BY 1"
    _validate_sql(good)
    print("OK: security guard accepts a well-formed mart-only SELECT")

    # QueryPlan self-check: an unresolvable field must be rejected by the
    # compiler itself, before _validate_sql ever runs.
    from query_plan import QueryFilters

    bad_plan = QueryPlan(intent="metric_lookup", metric="fare", filters=QueryFilters(hour=8))
    try:
        compile_plan(bad_plan, NYC_SCHEMA)
        raise AssertionError("should have rejected: zone_fare_stats has no hour column")
    except ValueError:
        pass
    print("OK: query_plan_compiler rejects a plan referencing an unresolvable field")

    result = answer("What is the average fare for trips picked up in JFK Airport?")
    print(f"\nplan:\n{result['plan']}\n\nSQL:\n{result['sql']}\n\nresult: {result['rows']}")


if __name__ == "__main__":
    demo()
