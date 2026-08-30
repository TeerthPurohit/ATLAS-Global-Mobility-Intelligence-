"""Coverage for mcp_server/server.py (SPEC-016): the MCP stdio server
wrapping rag/nl_to_sql/'s QueryPlan compiler pipeline. No logic is
reimplemented here -- every check either cross-checks a wrapped primitive
against the real rag/nl_to_sql/ function it delegates to, or proves the
wrapper's own thin dict-in/dict-out shape (e.g. that `compile_plan`'s
response never carries a `basis` key -- only `run_query`'s executed result
should, per docs/superpowers/specs/2026-08-29-mcp-queryplan-server-design.md).

`@mcp.tool()` in the installed mcp==1.29.1 SDK returns the original callable
unmodified, so every tool below is called directly as a plain function.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from mcp_server import server  # noqa: E402

from nl_to_sql.query_plan import QueryFilters, QueryPlan  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

GOOD_PLAN_DICT = {
    "intent": "metric_lookup",
    "metric": "fare",
    "aggregation": "avg",
    "filters": {"area": "JFK Airport"},
    "group_by": None,
    "order": None,
    "limit": None,
}

# The canonical unresolvable-field plan from sql_agent.py's own demo():
# zone_fare_stats has no hour column.
BAD_PLAN_DICT = {
    "intent": "metric_lookup",
    "metric": "fare",
    "filters": {"hour": 8},
    "aggregation": "count",
    "group_by": None,
    "order": None,
    "limit": None,
}


def test_describe_schema_matches_nyc_schema_describe():
    assert server.describe_schema() == {"schema": server.NYC_SCHEMA.describe()}


def test_compile_plan_matches_direct_compiler_call():
    good_plan = QueryPlan(
        intent="metric_lookup",
        metric="fare",
        aggregation="avg",
        filters=QueryFilters(area="JFK Airport"),
    )
    expected_sql = server.compile_plan_fn(good_plan, server.NYC_SCHEMA)

    result = server.compile_plan(GOOD_PLAN_DICT)
    assert result == {"sql": expected_sql}


def test_compile_plan_rejects_unresolvable_field():
    with pytest.raises(ValueError):
        server.compile_plan(BAD_PLAN_DICT)


def test_run_query_rejects_unresolvable_field():
    with pytest.raises(ValueError):
        server.run_query(BAD_PLAN_DICT)


def test_run_query_executes_and_tags_basis_computed():
    result = server.run_query(GOOD_PLAN_DICT)
    assert result["basis"] == "computed"
    assert result["source"] == "duckdb:nyc_rides"
    assert result["rows"]


def test_generate_plan_finetuned_disabled_by_default(monkeypatch):
    # Mirrors query_plan_agent.demo()'s own assertion style. Forced via
    # monkeypatch rather than relying on ambient env vars being unset --
    # this dev environment has USE_FINETUNED_QUERY_PLAN/
    # QUERY_PLAN_FINETUNED_MODEL_ID actually configured (the local
    # fine-tuned model is live, see memory.md), so the module-level
    # constants server.py imported are patched directly for this test.
    monkeypatch.setattr(server, "USE_FINETUNED_QUERY_PLAN", False)
    with pytest.raises(RuntimeError) as exc_info:
        server.generate_plan("What is the average fare for JFK Airport?", model="finetuned")
    assert "USE_FINETUNED_QUERY_PLAN" in str(exc_info.value)


def test_compile_plan_response_has_no_basis_key():
    # Regression guard: an earlier draft wrongly tagged intermediate
    # (non-executed) compile_plan results "computed" -- only run_query's
    # actually-executed result should carry a basis field.
    result = server.compile_plan(GOOD_PLAN_DICT)
    assert "basis" not in result


def demo() -> None:
    test_describe_schema_matches_nyc_schema_describe()
    test_compile_plan_matches_direct_compiler_call()
    test_compile_plan_rejects_unresolvable_field()
    test_run_query_rejects_unresolvable_field()
    test_run_query_executes_and_tags_basis_computed()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(server, "USE_FINETUNED_QUERY_PLAN", False)
        try:
            server.generate_plan("What is the average fare for JFK Airport?", model="finetuned")
            raise AssertionError("should have raised while USE_FINETUNED_QUERY_PLAN is unset")
        except RuntimeError as exc:
            assert "USE_FINETUNED_QUERY_PLAN" in str(exc)
    test_compile_plan_response_has_no_basis_key()
    print("test_mcp_server demo OK")


if __name__ == "__main__":
    if not WAREHOUSE_PATH.exists():
        print("SKIP: warehouse not built")
    else:
        demo()
