"""NL-to-SQL over the mart schema only (FR-3, ADR-004).

The LLM is prompted with the mart *schema* (table/column names + types,
read live from `information_schema` so it can't drift from the marts),
never raw trip-level tables -- a hard boundary per
docs/architecture/Security.md. It is only ever allowed to write a single
read-only SELECT: the connection it runs against is opened `read_only`,
and `_validate_sql()` independently checks the generated text against a
table allow-list and a DDL/DML keyword blocklist before execution, so a
malformed or prompt-injected query can only ever "wrong read" a mart, never
write, drop, or touch raw trip rows.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEFAULT_DB_PATH, OPENAI_MODEL  # noqa: E402

ALLOWED_TABLES = {"zone_hourly_demand", "zone_fare_stats", "zone_pair_flows"}

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|export|import|"
    r"pragma|call|grant|vacuum|checkpoint|replace)\b",
    re.IGNORECASE,
)
_STARTS_SELECT = re.compile(r"^\s*(with|select)\b", re.IGNORECASE)
_CTE_NAME_RE = re.compile(r"\b(\w+)\s+as\s*\(", re.IGNORECASE)
_TABLE_REF_RE = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)

SYSTEM_PROMPT_TEMPLATE = """You are a SQL analyst for a NYC ride-hailing data \
platform. Given a user's question, write exactly ONE read-only DuckDB SQL \
SELECT statement that answers it, using ONLY the tables and columns listed \
below. These are pre-aggregated summary tables (marts), not raw trip rows.

{schema}

Rules, no exceptions:
- Output ONLY the SQL. No explanation, no markdown code fences, no comments.
- Exactly one statement, starting with SELECT or WITH.
- Never reference any table other than the ones listed above.
- If the question asks for a filter these tables have no column for (e.g. an \
hour-of-day filter on a table with no hour column), write the closest correct \
query using only the available columns -- never invent a column.
"""


def get_mart_schema(con: duckdb.DuckDBPyConnection) -> str:
    rows = con.execute(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_name = ANY(?) ORDER BY table_name, ordinal_position",
        [list(ALLOWED_TABLES)],
    ).fetchall()
    tables: dict[str, list[str]] = {}
    for table, col, dtype in rows:
        tables.setdefault(table, []).append(f"{col} {dtype}")
    return "\n\n".join(f"TABLE {t} (\n  " + ",\n  ".join(cols) + "\n)" for t, cols in tables.items())


def _strip_fences(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = re.sub(r"^```[a-zA-Z]*\n?", "", sql)
        sql = re.sub(r"```$", "", sql).strip()
    return sql.rstrip(";").strip()


def _validate_sql(sql: str) -> None:
    if not _STARTS_SELECT.match(sql):
        raise ValueError(f"generated SQL must start with SELECT or WITH: {sql!r}")
    if ";" in sql:
        raise ValueError(f"generated SQL must be a single statement: {sql!r}")
    if _FORBIDDEN_KEYWORDS.search(sql):
        raise ValueError(f"generated SQL contains a forbidden keyword: {sql!r}")

    cte_names = {m.lower() for m in _CTE_NAME_RE.findall(sql)}
    referenced = {m.lower() for m in _TABLE_REF_RE.findall(sql)}
    allowed = {t.lower() for t in ALLOWED_TABLES} | cte_names
    illegal = referenced - allowed
    if illegal:
        raise ValueError(f"generated SQL references disallowed table(s) {illegal}: {sql!r}")


def generate_sql(question: str, schema: str, model: str = OPENAI_MODEL) -> str:
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(schema=schema)},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_completion_tokens=400,
    )
    return _strip_fences(resp.choices[0].message.content or "")


def answer(question: str, db_path: Path = DEFAULT_DB_PATH, model: str = OPENAI_MODEL) -> dict:
    """Generate SQL for `question`, validate it, run it read-only, return
    the query alongside the real result (never a value the LLM invented)."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        schema = get_mart_schema(con)
        sql = generate_sql(question, schema, model=model)
        _validate_sql(sql)
        df = con.execute(sql).df()
    finally:
        con.close()
    return {
        "question": question,
        "sql": sql,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }


def demo() -> None:
    # Security guard self-check: every one of these must be rejected before
    # ever reaching a live connection.
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

    result = answer("What is the average fare for trips picked up in JFK Airport?")
    print(f"\nSQL:\n{result['sql']}\n\nresult: {result['rows']}")


if __name__ == "__main__":
    demo()
