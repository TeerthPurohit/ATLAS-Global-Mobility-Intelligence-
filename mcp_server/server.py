"""MCP stdio server wrapping rag/nl_to_sql/'s QueryPlan compiler pipeline
(SPEC-016). Pure reuse -- no schema resolution, SQL compilation, or
security guard logic is reimplemented here; every primitive below is a
thin call into an already-tested rag/nl_to_sql/ function. See
docs/superpowers/specs/2026-08-29-mcp-queryplan-server-design.md for the
full design, including why `describe_schema` is both a Tool and a
Resource, and why only `run_query` carries a `basis` field.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import duckdb
from mcp.server.fastmcp import FastMCP

RAG_DIR = Path(__file__).resolve().parents[1] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from config import DEFAULT_DB_PATH  # noqa: E402
from nl_to_sql.nyc_schema import NYC_SCHEMA  # noqa: E402
from nl_to_sql.query_plan import QueryPlan  # noqa: E402
from nl_to_sql.query_plan_compiler import compile as compile_plan_fn  # noqa: E402
from nl_to_sql.query_plan_agent import (  # noqa: E402
    FINETUNED_MODEL_ID,
    USE_FINETUNED_QUERY_PLAN,
    generate_plan as generate_plan_finetuned,
)
from nl_to_sql.sql_agent import (  # noqa: E402
    _validate_sql,
    generate_plan as generate_plan_base,
)

mcp = FastMCP("nyc-mobility-queryplan")


def _schema_payload() -> dict:
    return {"schema": NYC_SCHEMA.describe()}


@mcp.tool()
def describe_schema() -> dict:
    """Canonical mobility schema (tables/columns/types) the QueryPlan compiler resolves against."""
    return _schema_payload()


@mcp.resource("schema://nyc-mobility")
def describe_schema_resource() -> dict:
    """Same payload as the describe_schema tool, exposed as a manually-attachable Resource."""
    return _schema_payload()


@mcp.tool()
def generate_plan(question: str, model: Literal["base", "finetuned"] = "base") -> dict:
    """Natural-language question -> QueryPlan JSON (not SQL, not executed)."""
    if model == "finetuned":
        if not USE_FINETUNED_QUERY_PLAN:
            raise RuntimeError("query_plan_agent is disabled -- set USE_FINETUNED_QUERY_PLAN=1 to enable")
        if not FINETUNED_MODEL_ID:
            raise RuntimeError(
                "USE_FINETUNED_QUERY_PLAN is on but QUERY_PLAN_FINETUNED_MODEL_ID is unset -- no "
                "fine-tuned model has been trained yet (spec-014 FR-7, submitted/run separately)"
            )
        plan = generate_plan_finetuned(question, NYC_SCHEMA, FINETUNED_MODEL_ID)
    else:
        plan = generate_plan_base(question, schema=NYC_SCHEMA)
    return {"plan": plan.to_dict()}


@mcp.tool()
def compile_plan(plan: dict) -> dict:
    """Compile a QueryPlan dict to SQL. Raises ValueError for an unresolvable field."""
    qp = QueryPlan.from_dict(plan)
    sql = compile_plan_fn(qp, NYC_SCHEMA)
    return {"sql": sql}


@mcp.tool()
def run_query(plan: dict) -> dict:
    """Compile a QueryPlan dict and execute it read-only against the warehouse."""
    qp = QueryPlan.from_dict(plan)
    sql = compile_plan_fn(qp, NYC_SCHEMA)
    _validate_sql(sql, {m.table for m in NYC_SCHEMA.metrics.values()})

    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        df = con.execute(sql).df()
    finally:
        con.close()
    return {
        "basis": "computed",
        "source": f"duckdb:{DEFAULT_DB_PATH.stem}",
        "sql": sql,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
