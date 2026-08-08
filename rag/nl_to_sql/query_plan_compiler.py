"""Deterministic QueryPlan -> SQL compiler (FR-2, spec-014).

The LLM (base or, later, fine-tuned) only ever produces a `QueryPlan` --
structured intent/metric/filters JSON, never SQL text. This module is the
only place that turns a plan into SQL, and it only ever emits schema-
declared table and column names (never anything the plan/LLM supplied as a
raw string); the sole untrusted input is filter *values* (e.g. an area
name), which are validated by type and escaped, never concatenated raw --
this is the injection-safety win noted in spec-014: the LLM never writes SQL
text. Every canonical field a plan references is resolved against the given
`CityMobilitySchema` *before* any SQL text is built; an unresolvable field
raises rather than emitting a partial/guessed query, matching sql_agent.py's
"never invent a column" discipline (ADR-004).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from query_plan import AGGREGATIONS, CityMobilitySchema, QueryPlan  # noqa: E402

_AGG_SQL = {"count": "COUNT", "avg": "AVG", "sum": "SUM", "max": "MAX", "min": "MIN"}

# Intents that rank/list rows across a dimension default to grouping by
# "area" unless the plan says otherwise; "hourly_pattern" defaults to "hour".
# "metric_lookup" never groups unless the plan explicitly asks it to.
_DEFAULT_GROUP_BY = {
    "area_ranking": "area",
    "top_n": "area",
    "comparison": "area",
    "hourly_pattern": "hour",
}


def _group_by_name(plan: QueryPlan) -> str | None:
    if plan.group_by:
        return plan.group_by
    if plan.intent == "metric_lookup":
        return None
    return _DEFAULT_GROUP_BY.get(plan.intent)


def _sql_literal(value: object, is_text: bool) -> str:
    if is_text:
        if not isinstance(value, str):
            raise ValueError(f"expected a text value, got {value!r}")
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected a numeric value, got {value!r}")
    return str(value)


def validate_plan(plan: QueryPlan, schema: CityMobilitySchema) -> None:
    """Resolve every field the plan references against `schema`; raises
    before any SQL text is built if a field can't be resolved."""
    schema.resolve_metric(plan.metric)  # raises for an unknown metric

    for canonical_field in plan.filters.active():
        schema.resolve_field(plan.metric, canonical_field)

    group_by_name = _group_by_name(plan)
    if group_by_name:
        schema.resolve_field(plan.metric, group_by_name)

    if plan.aggregation not in AGGREGATIONS:
        raise ValueError(f"unknown aggregation {plan.aggregation!r}")
    if plan.order and plan.order not in ("asc", "desc"):
        raise ValueError(f"unknown order {plan.order!r}")
    if plan.limit is not None and (isinstance(plan.limit, bool) or not isinstance(plan.limit, int) or plan.limit <= 0):
        raise ValueError(f"limit must be a positive integer, got {plan.limit!r}")


def compile(plan: QueryPlan, schema: CityMobilitySchema) -> str:  # noqa: A001 -- matches spec's `compile(plan, schema)`
    validate_plan(plan, schema)
    metric_schema = schema.resolve_metric(plan.metric)
    metric_expr = f"{_AGG_SQL[plan.aggregation]}({metric_schema.value.column}) AS {plan.metric}"

    where_clauses: list[str] = []
    for canonical_field, value in plan.filters.active().items():
        field_map = schema.resolve_field(plan.metric, canonical_field)
        if canonical_field == "date_range":
            start, end = value
            where_clauses.append(
                f"{field_map.column} BETWEEN {_sql_literal(start, True)} AND {_sql_literal(end, True)}"
            )
        else:
            where_clauses.append(f"{field_map.column} = {_sql_literal(value, field_map.is_text)}")

    group_by_name = _group_by_name(plan)
    select_cols: list[str] = []
    group_col: str | None = None
    if group_by_name:
        group_col = schema.resolve_field(plan.metric, group_by_name).column
        select_cols.append(group_col)
    select_cols.append(metric_expr)

    sql = f"SELECT {', '.join(select_cols)} FROM {metric_schema.table}"
    if where_clauses:
        sql += f" WHERE {' AND '.join(where_clauses)}"
    if group_col:
        sql += f" GROUP BY {group_col}"

    if plan.order:
        sql += f" ORDER BY {plan.metric} {plan.order.upper()}"
    elif plan.intent == "hourly_pattern" and group_col:
        sql += f" ORDER BY {group_col} ASC"  # chronological by default, not ranked

    if plan.limit:
        sql += f" LIMIT {plan.limit}"

    return sql


def demo() -> None:
    from query_plan import QueryFilters  # noqa: E402
    from nyc_schema import NYC_SCHEMA  # noqa: E402

    plan = QueryPlan(
        intent="metric_lookup", metric="fare", aggregation="avg", filters=QueryFilters(area="JFK Airport")
    )
    sql = compile(plan, NYC_SCHEMA)
    assert sql == "SELECT AVG(avg_fare) AS fare FROM zone_fare_stats WHERE pickup_zone = 'JFK Airport'"
    print(f"OK: {sql}")

    bad_plan = QueryPlan(intent="metric_lookup", metric="fare", filters=QueryFilters(hour=8))
    try:
        compile(bad_plan, NYC_SCHEMA)
        raise AssertionError("should have raised: zone_fare_stats has no hour column")
    except ValueError:
        pass
    print("OK: unresolvable field raises instead of emitting a guessed query")


if __name__ == "__main__":
    demo()
