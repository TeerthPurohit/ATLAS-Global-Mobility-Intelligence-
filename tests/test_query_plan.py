"""Compiler correctness per canonical intent against nyc_schema.py, and the
"raise rather than guess" guarantee for an unresolvable field (spec-014,
FR-2/FR-3). No LLM call anywhere in this file -- QueryPlan objects are
constructed directly, exactly mirroring how a fine-tuned model's *parsed*
output would be handed to the compiler.
"""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "nl_to_sql"))

import query_plan_compiler as qpc  # noqa: E402
from nyc_schema import NYC_SCHEMA  # noqa: E402
from query_plan import QueryFilters, QueryPlan  # noqa: E402
from query_plan_compiler import compile as compile_plan  # noqa: E402


# ---- one correctness case per canonical intent ----

def test_metric_lookup_compiles():
    plan = QueryPlan(intent="metric_lookup", metric="fare", aggregation="avg", filters=QueryFilters(area="JFK Airport"))
    sql = compile_plan(plan, NYC_SCHEMA)
    assert sql == "SELECT AVG(avg_fare) AS fare FROM zone_fare_stats WHERE pickup_zone = 'JFK Airport'"


def test_area_ranking_compiles():
    plan = QueryPlan(intent="area_ranking", metric="demand", aggregation="sum", order="desc", limit=1)
    sql = compile_plan(plan, NYC_SCHEMA)
    assert sql == (
        "SELECT pickup_location_id, SUM(total_trips) AS demand FROM zone_hourly_demand "
        "GROUP BY pickup_location_id ORDER BY demand DESC LIMIT 1"
    )


def test_top_n_compiles():
    plan = QueryPlan(intent="top_n", metric="flow", aggregation="sum", order="desc", limit=5)
    sql = compile_plan(plan, NYC_SCHEMA)
    assert sql == (
        "SELECT pickup_zone, SUM(trip_count) AS flow FROM zone_pair_flows "
        "GROUP BY pickup_zone ORDER BY flow DESC LIMIT 5"
    )


def test_comparison_compiles():
    plan = QueryPlan(intent="comparison", metric="fare", aggregation="avg")
    sql = compile_plan(plan, NYC_SCHEMA)
    assert sql == "SELECT pickup_zone, AVG(avg_fare) AS fare FROM zone_fare_stats GROUP BY pickup_zone"


def test_hourly_pattern_compiles():
    plan = QueryPlan(intent="hourly_pattern", metric="demand", aggregation="avg")
    sql = compile_plan(plan, NYC_SCHEMA)
    assert sql == (
        "SELECT pickup_hour, AVG(total_trips) AS demand FROM zone_hourly_demand "
        "GROUP BY pickup_hour ORDER BY pickup_hour ASC"
    )


# ---- unresolvable fields raise, never emit a partial/guessed query ----

@pytest.mark.parametrize(
    "plan",
    [
        QueryPlan(intent="metric_lookup", metric="fare", filters=QueryFilters(hour=8)),  # no hour column on fare
        QueryPlan(intent="metric_lookup", metric="demand", filters=QueryFilters(day_of_week=1)),  # no mart has this
        QueryPlan(intent="hourly_pattern", metric="fare"),  # group_by defaults to hour, unresolvable for fare
        QueryPlan(intent="metric_lookup", metric="not_a_real_metric"),  # type: ignore[arg-type]
    ],
)
def test_unresolvable_field_raises(plan):
    with pytest.raises(ValueError):
        compile_plan(plan, NYC_SCHEMA)


def test_bad_aggregation_raises():
    plan = QueryPlan(intent="metric_lookup", metric="fare", aggregation="median")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        compile_plan(plan, NYC_SCHEMA)


# ---- no code path here constructs SQL by concatenating raw LLM text ----

def test_compiler_never_touches_raw_llm_text():
    src = inspect.getsource(qpc)
    assert "question" not in src
    assert "openai" not in src.lower()
    assert "response" not in src.lower()
