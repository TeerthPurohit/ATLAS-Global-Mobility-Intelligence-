"""Four invented, non-NYC CityMobilitySchema instances (FR-4, spec-014).

These exist *only* to generate schema-agnostic training/eval examples for
the QueryPlan fine-tune -- each invents different table/column names for the
same five canonical concepts (demand/fare/flow value columns, plus
area/hour/day_of_week/date_range filters), and clearly fictional area labels
(no real city's zone/borough names, and no NYC boroughs renamed). None of
these are ever connected to a real database or presented as a real city's
schema -- a real second city's pipeline would have its own real
schema and is not related to these. To avoid any chance of that conflation,
these are deliberately named generically (alpha/beta/gamma/delta) rather
than after any real or fictional-but-plausible city.

No trip counts, fares, or other mobility *data* are invented here -- only
column names and short descriptions of what a column means, exactly the
same shape `describe()` renders for NYC.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from query_plan import CityMobilitySchema, FieldMapping, MetricSchema


def _full_coverage_schema(
    name: str,
    *,
    demand_table: str,
    demand_col: str,
    fare_table: str,
    fare_col: str,
    flow_table: str,
    flow_col: str,
    area_col: str,
    hour_col: str,
    dow_col: str,
    date_col: str,
) -> CityMobilitySchema:
    """Every synthetic schema gives full canonical-field coverage on all
    three metrics -- unlike NYC's real (partial) mart coverage, this keeps
    the four synthetic schemas directly comparable to each other for the
    generalization eval (FR-6), rather than one accidentally being an easier
    or harder held-out schema because of which filters happen to exist."""
    filters = {
        "area": FieldMapping(area_col, "pickup area identifier", is_text=True),
        "hour": FieldMapping(hour_col, "hour of day, 0-23"),
        "day_of_week": FieldMapping(dow_col, "day of week, 0-6"),
        "date_range": FieldMapping(date_col, "calendar date"),
    }
    return CityMobilitySchema(
        name=name,
        metrics={
            "demand": MetricSchema(
                table=demand_table,
                value=FieldMapping(demand_col, "count of trips"),
                filters=dict(filters),
            ),
            "fare": MetricSchema(
                table=fare_table,
                value=FieldMapping(fare_col, "average fare amount"),
                filters=dict(filters),
            ),
            "flow": MetricSchema(
                table=flow_table,
                value=FieldMapping(flow_col, "count of trips between an area pair"),
                filters=dict(filters),
            ),
        },
    )


SCHEMA_ALPHA = _full_coverage_schema(
    "schema_alpha",
    demand_table="journey_counts",
    demand_col="ride_count",
    fare_table="fare_summary",
    fare_col="avg_fare_amount",
    flow_table="route_flow_summary",
    flow_col="trip_count",
    area_col="pickup_zone",
    hour_col="start_hour",
    dow_col="start_dow",
    date_col="journey_date",
)

SCHEMA_BETA = _full_coverage_schema(
    "schema_beta",
    demand_table="trip_volume",
    demand_col="trip_total",
    fare_table="fare_details",
    fare_col="fare_inr",
    flow_table="area_pair_traffic",
    flow_col="journey_count",
    area_col="pickup_area",
    hour_col="start_hour_local",
    dow_col="start_weekday",
    date_col="start_date",
)

SCHEMA_GAMMA = _full_coverage_schema(
    "schema_gamma",
    demand_table="rental_activity",
    demand_col="rental_count",
    fare_table="cost_breakdown",
    fare_col="avg_cost",
    flow_table="station_pair_trips",
    flow_col="trip_total",
    area_col="origin_station",
    hour_col="checkout_hour",
    dow_col="checkout_weekday",
    date_col="checkout_date",
)

# Held out entirely from training (FR-6) -- never seen during fine-tuning,
# used only for the generalization eval.
SCHEMA_DELTA = _full_coverage_schema(
    "schema_delta",
    demand_table="boarding_counts",
    demand_col="boardings",
    fare_table="ticket_prices",
    fare_col="avg_ticket_price",
    flow_table="route_segment_flow",
    flow_col="passenger_count",
    area_col="stop_zone",
    hour_col="boarding_hour",
    dow_col="boarding_dow",
    date_col="service_date",
)

TRAIN_SYNTHETIC_SCHEMAS = (SCHEMA_ALPHA, SCHEMA_BETA, SCHEMA_GAMMA)
HELD_OUT_SCHEMA = SCHEMA_DELTA
ALL_SYNTHETIC_SCHEMAS = (SCHEMA_ALPHA, SCHEMA_BETA, SCHEMA_GAMMA, SCHEMA_DELTA)


def demo() -> None:
    names = {s.name for s in ALL_SYNTHETIC_SCHEMAS}
    assert len(names) == 4, "all four synthetic schemas must have distinct names"
    assert HELD_OUT_SCHEMA not in TRAIN_SYNTHETIC_SCHEMAS
    for schema in ALL_SYNTHETIC_SCHEMAS:
        for metric in ("demand", "fare", "flow"):
            for canonical in ("area", "hour", "day_of_week", "date_range"):
                assert schema.has_field(metric, canonical), f"{schema.name}/{metric} missing {canonical}"
        assert f"TABLE {schema.metrics['demand'].table}" in schema.describe()
    print(f"OK: 4 synthetic schemas ({', '.join(sorted(names))}), full canonical coverage, all resolvable")


if __name__ == "__main__":
    demo()
