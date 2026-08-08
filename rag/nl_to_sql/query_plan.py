"""Schema-agnostic QueryPlan + per-city schema resolver (FR-1, spec-014).

Today's NL-to-SQL (`sql_agent.py`) prompts an LLM straight into NYC's real
column names -- a model fine-tuned on that would not transfer to a second
city with different columns. `QueryPlan` is the schema-agnostic target
instead: intent/metric/filters/aggregation, never a table or column name.
`CityMobilitySchema` is the per-city (or, for training/eval only, per-
synthetic-schema) resolver that turns a plan's canonical field names into
real `(table, column)` pairs -- see `query_plan_compiler.py` for the
compiler that actually builds SQL from a resolved plan.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal

Intent = Literal["area_ranking", "metric_lookup", "top_n", "comparison", "hourly_pattern"]
Metric = Literal["demand", "fare", "flow"]
Aggregation = Literal["count", "avg", "sum", "max", "min"]
Order = Literal["asc", "desc"]

INTENTS: tuple[Intent, ...] = ("area_ranking", "metric_lookup", "top_n", "comparison", "hourly_pattern")
METRICS: tuple[Metric, ...] = ("demand", "fare", "flow")
AGGREGATIONS: tuple[Aggregation, ...] = ("count", "avg", "sum", "max", "min")

# Canonical filter/group-by concepts a CityMobilitySchema may resolve, beyond
# a metric's own value column. Not every schema/metric resolves every one of
# these -- e.g. NYC's `zone_fare_stats` mart has no hour column, so "hour" is
# simply absent from that metric's `filters` map (see nyc_schema.py).
CANONICAL_FIELDS = ("area", "hour", "day_of_week", "date_range")


@dataclass
class QueryFilters:
    hour: int | None = None
    day_of_week: int | None = None
    area: str | int | None = None
    date_range: tuple[str, str] | None = None

    def active(self) -> dict[str, object]:
        """Only the filters actually set, as canonical-name -> value."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class QueryPlan:
    intent: Intent
    metric: Metric
    filters: QueryFilters = field(default_factory=QueryFilters)
    aggregation: Aggregation = "count"
    group_by: str | None = None
    order: Order | None = None
    limit: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def from_dict(data: dict) -> "QueryPlan":
        filters_data = data.get("filters") or {}
        date_range = filters_data.get("date_range")
        filters = QueryFilters(
            hour=filters_data.get("hour"),
            day_of_week=filters_data.get("day_of_week"),
            area=filters_data.get("area"),
            date_range=tuple(date_range) if date_range else None,  # type: ignore[arg-type]
        )
        return QueryPlan(
            intent=data["intent"],
            metric=data["metric"],
            filters=filters,
            aggregation=data.get("aggregation", "count"),
            group_by=data.get("group_by"),
            order=data.get("order"),
            limit=data.get("limit"),
        )

    @staticmethod
    def from_json(text: str) -> "QueryPlan":
        return QueryPlan.from_dict(json.loads(text))


@dataclass(frozen=True)
class FieldMapping:
    """One canonical concept's real column, plus whether it needs SQL string
    quoting (`is_text`) -- e.g. NYC's demand mart keys area by a numeric zone
    id, but its fare/flow marts only carry the zone name as text."""

    column: str
    meaning: str
    is_text: bool = False


@dataclass(frozen=True)
class MetricSchema:
    """A canonical metric's backing table, its own value column, and every
    other canonical field (area/hour/day_of_week/date_range) that table
    actually exposes -- only entries a real query could use are present."""

    table: str
    value: FieldMapping
    filters: dict[str, FieldMapping] = field(default_factory=dict)


@dataclass(frozen=True)
class CityMobilitySchema:
    """Canonical field name -> real (table, column), scoped per metric since
    the same canonical concept (e.g. "area") can live on a different column
    -- even a different type -- depending on which metric's table it's on.
    Same shape for NYC (`nyc_schema.py`) and every synthetic schema
    (`synthetic_schemas.py`) so a QueryPlan-producing model never sees a
    NYC-vs-synthetic tell, only "a schema description."
    """

    name: str
    metrics: dict[str, MetricSchema]

    def __post_init__(self) -> None:
        unknown = set(self.metrics) - set(METRICS)
        if unknown:
            raise ValueError(f"{self.name}: unknown metric key(s) {sorted(unknown)} (must be one of {METRICS})")

    def resolve_metric(self, metric: str) -> MetricSchema:
        if metric not in self.metrics:
            raise ValueError(f"{self.name}: metric {metric!r} is not resolvable in this schema")
        return self.metrics[metric]

    def resolve_field(self, metric: str, canonical_field: str) -> FieldMapping:
        m = self.resolve_metric(metric)
        if canonical_field not in m.filters:
            raise ValueError(
                f"{self.name}: metric {metric!r} has no resolvable field {canonical_field!r} "
                f"(available: {sorted(m.filters)})"
            )
        return m.filters[canonical_field]

    def has_field(self, metric: str, canonical_field: str) -> bool:
        m = self.metrics.get(metric)
        return bool(m and canonical_field in m.filters)

    def describe(self) -> str:
        """Compact `TABLE <name> (<column> -- <canonical>: <meaning>, ...)`
        text for LLM context -- mirrors `sql_agent.get_mart_schema()`'s
        rendering style so both NL-to-SQL paths read the same to a model."""
        by_table: dict[str, list[str]] = {}
        for metric_name, m in self.metrics.items():
            cols = by_table.setdefault(m.table, [])
            value_entry = f"{m.value.column} -- {metric_name}: {m.value.meaning}"
            if value_entry not in cols:
                cols.append(value_entry)
            for canonical, fmap in m.filters.items():
                entry = f"{fmap.column} -- {canonical}: {fmap.meaning}"
                if entry not in cols:
                    cols.append(entry)
        return "\n\n".join(f"TABLE {t} (\n  " + ",\n  ".join(cols) + "\n)" for t, cols in by_table.items())


def demo() -> None:
    plan = QueryPlan(
        intent="metric_lookup",
        metric="fare",
        aggregation="avg",
        filters=QueryFilters(area="JFK Airport"),
    )
    round_tripped = QueryPlan.from_json(plan.to_json())
    assert round_tripped == plan, "QueryPlan must round-trip through JSON unchanged"

    schema = CityMobilitySchema(
        name="demo",
        metrics={
            "fare": MetricSchema(
                table="fare_table",
                value=FieldMapping("avg_fare", "average fare"),
                filters={"area": FieldMapping("zone_name", "pickup zone", is_text=True)},
            )
        },
    )
    assert schema.resolve_field("fare", "area").column == "zone_name"
    assert schema.has_field("fare", "area") and not schema.has_field("fare", "hour")
    assert "TABLE fare_table" in schema.describe()
    print("OK: QueryPlan JSON round-trip and CityMobilitySchema resolution")


if __name__ == "__main__":
    demo()
