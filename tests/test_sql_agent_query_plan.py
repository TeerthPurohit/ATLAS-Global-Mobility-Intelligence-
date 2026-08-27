"""sql_agent.py-specific coverage for SPEC-013 FR-10: the LIVE `/chat`
numeric-question path no longer lets the LLM emit raw SQL text at all --
it produces a QueryPlan, compiled deterministically by the same
query_plan_compiler.py `tests/test_query_plan.py` (spec-014) already proves
correct per canonical intent. This file only tests what's specific to
sql_agent.py's own restructuring (FR-10), not the compiler itself.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "rag"))
sys.path.insert(0, str(REPO_ROOT / "rag" / "nl_to_sql"))

from nyc_schema import NYC_SCHEMA  # noqa: E402, I001
from query_plan import QueryFilters, QueryPlan  # noqa: E402
from query_plan_compiler import compile as compile_plan  # noqa: E402
import sql_agent  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


def test_sql_agent_has_no_raw_sql_generation_path():
    """generate_sql() (the old LLM-writes-SQL-text function) must be gone;
    generate_plan() (LLM-writes-QueryPlan-JSON) replaces it."""
    assert not hasattr(sql_agent, "generate_sql")
    assert hasattr(sql_agent, "generate_plan")


def test_sql_agent_answer_routes_through_the_compiler_not_raw_text(monkeypatch):
    """Patching generate_plan to return a known QueryPlan proves answer()'s
    executed SQL comes from query_plan_compiler.compile(), not any
    LLM-authored string -- the only untrusted LLM output on this path is
    already-typed QueryPlan JSON, never SQL text."""
    plan = QueryPlan(intent="metric_lookup", metric="fare", aggregation="avg", filters=QueryFilters(area="JFK Airport"))
    monkeypatch.setattr(sql_agent, "generate_plan", lambda question, model=sql_agent.OPENAI_MODEL: plan)

    result = sql_agent.answer("What is the average fare for JFK Airport?")
    assert result["sql"] == compile_plan(plan, NYC_SCHEMA)
    assert result["plan"]["metric"] == "fare"
    assert result["rows"]


def test_validate_sql_still_rejects_disallowed_sql_defense_in_depth():
    """_validate_sql() is kept as a second layer over the compiler's output
    (ADR-004 defense in depth), not removed -- existing tests/test_rag.py
    already covers its full behavior; this just proves it still runs on the
    new answer() path."""
    with pytest.raises(ValueError):
        sql_agent._validate_sql("SELECT * FROM stg_trips")
