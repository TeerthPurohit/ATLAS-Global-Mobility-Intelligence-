# ADR-002: staging / intermediate / marts layering in dbt

**Status:** Accepted (Layer 1, in progress)

## Context

Raw HVFHV trip data needs to become query-ready tables for algorithms, ML,
and RAG, without every downstream consumer re-deriving the same joins and
casts.

## Decision

Three-layer dbt structure, each layer with exactly one job:

- **staging** (`stg_trips`, `stg_zones`): cast types, rename to snake_case,
  drop clearly broken rows. No business logic, no joins to other domains.
- **intermediate** (`int_trips_enriched`): join trips to zones, derive
  `hour_of_day`, `day_of_week`, `is_weekend`, `trip_duration_minutes`,
  `avg_speed_mph`.
- **marts** (`zone_hourly_demand`, `zone_fare_stats`, `zone_pair_flows`):
  answer a specific business question each; everything downstream reads
  only from here.

## Why

Each layer has a single reason to change: staging changes if the raw
source schema changes; intermediate changes if enrichment logic changes;
marts change if a downstream question changes. Collapsing layers means a
schema change anywhere forces re-auditing every consumer's SQL. This also
means `zone_hourly_demand` (the ML target) and `zone_pair_flows` (the graph
input) can each evolve independently once intermediate is stable.

## Consequences

- More files than a flat structure — acceptable given only ~9 models total
  at this project's scale.
- `int_trips_enriched` is a single point every mart depends on; a bug there
  propagates to all three marts. Mitigated by dbt tests on intermediate
  columns (see `dbt_project/models/intermediate/schema.yml`), not just marts.

## Related

Incremental-vs-full-refresh for `zone_hourly_demand` is a separate, still
open decision — tracked in `.claude/memory.md` and
`specs/002-dbt-transformation/spec.md`, not decided here.
