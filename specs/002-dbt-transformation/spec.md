# SPEC-002: dbt Transformation Layer

Owner: solo builder · Status: done · Layer: 1 · Depends on: SPEC-001

## Business Goal

Turn raw trip rows into clean, tested, query-ready marts that every later
layer reads from. `zone_hourly_demand` is the ML target variable — it has
to be right, everything downstream depends on it.

## Functional Requirements

- FR-1: `stg_trips.sql` — cast, rename to snake_case, drop rows with
  non-positive or implausible (>= $1000) total fare. Light cleaning only.
- FR-2: `stg_zones.sql` — clean zone lookup, dedupe if needed.
- FR-3: `int_trips_enriched.sql` — join trips to zones, derive
  `hour_of_day`, `day_of_week`, `is_weekend`, `trip_duration_minutes`,
  `avg_speed_mph`.
- FR-4: `zone_hourly_demand.sql` — group by zone/date/hour, pickup counts.
- FR-5: `zone_fare_stats.sql` — avg/median/percentile fares per zone-hour.
- FR-6: `zone_pair_flows.sql` — group by PULocationID/DOLocationID, trip
  counts (feeds Layer 2 graph).
- FR-7: dbt tests: `not_null` on zone IDs, `accepted_range` on fares,
  relationship test from trips to zone lookup.

## Current State

All 6 models exist and are actively being edited (git status shows
`int_trips_enriched.sql`, `zone_hourly_demand.sql`, `stg_trips.sql`, and
both `schema.yml` files modified as of this snapshot). `stg_trips.sql`
already derives `total_amount` from HVFHV's fare component columns since
HVFHV has no native `fare_amount`/`total_amount` (see
`.claude/memory.md`). `dbt test` has not yet been confirmed to pass clean —
that's the immediate next step, not `dbt run` alone.

## Non-Functional Requirements

- Reproducibility: `dbt run` + `dbt test` must be deterministic given the
  same raw table.

## Data Design

Grain: `zone_hourly_demand` is one row per (pickup zone, date, hour).
Open question, not yet resolved: incremental (append new days) vs
full-refresh. Given the dataset is a fixed 3-month historical batch (not a
growing daily feed for this project's scope), full-refresh is the likely
answer — but decide explicitly and record it as ADR-007 when resolved,
don't leave it implicit in the materialization config.

## Testing

`dbt test` clean pass is the bar — not just `dbt run` succeeding. Run
`dbt docs generate` once done and keep the lineage graph (portfolio
artifact per `project_plan.md`).

## Acceptance Criteria

- [x] All 6 models written.
- [ ] `dbt test` passes clean.
- [ ] Incremental-vs-full-refresh decision made and recorded (ADR-007).
- [ ] `dbt docs generate` run, lineage graph screenshot saved.
