# SPEC-015: London (real second city) + cross-city demand estimation

> **SUPERSEDED (2026-08-23) by [ADR-011](../../docs/adr/ADR-011-retreat-from-global-coverage.md).**
> London itself survives -- it has real data. The cross-city estimation half
> of this spec (population-scaled demand, PPP-scaled fares) was removed with
> the global layer.

Owner: solo builder · Status: draft · Layer: 5+ (extends Layers 0, 1, 3, 5) ·
Depends on: SPEC-002, SPEC-006, SPEC-013 (paused domain model/registry)

## Business Goal

Scale mobility intelligence to many GeoNames-discovered cities honestly,
in three tiers, instead of pretending every city has NYC-grade data:

1. **Real** — a real, trained model on real trip-level data. Today: NYC. This
   spec adds London, because TfL genuinely publishes trip-level Santander
   Cycle Hire journey data (journey id, bike id, timestamp, docking
   station-to-station, since Sept 2015) -- structurally the same shape as
   NYC's HVFHV data (origin, destination, timestamp), so the same pipeline
   pattern (staging -> marts -> KD-tree/PageRank/EWMA -> XGBoost) applies.
2. **Estimated** — `basis="modeled_estimate"`, a documented statistical
   scaling from the real cities' demand-per-capita using population density
   (GeoNames already returns real population figures -- no new data source).
   Explicitly NOT a trained model and never presented as one.
3. **Unavailable** — no covariate data resolvable either. Honest `unavailable`,
   never a silent zero (rule 2, ADR-007).

This directly extends SPEC-013's paused City/Country registry (which was
scoped "NYC-only, architecture-only" -- this spec is the deliberate,
explicit reason that scoping changes, not a silent reversal of it) and
reuses SPEC-013's dbt-seed-backed registry pattern.

Fare prediction is explicitly **not** attempted for London or any estimated
city: cycle hire isn't distance/time-variable priced like a taxi, and no
honest fare covariate exists for the estimated tier -- `fare_prediction`
capability stays `false` for every city except NYC.

## Functional Requirements

- FR-1: `scripts/ingest_tfl_cycle_hire.py` -- downloads/loads TfL Santander
  Cycle Hire journey CSVs (cycling.data.tfl.gov.uk) into
  `data/warehouse/london_cycles.duckdb`, mirroring
  `scripts/load_raw_to_duckdb.py`'s pattern for NYC's raw parquet load.
- FR-2: `dbt_project/models/staging/stg_london_cycle_journeys.sql`,
  `dbt_project/models/marts/london_station_hourly_demand.sql` -- same
  staging -> mart layering discipline as NYC (rule 6), grain: trips per
  docking station per hour, mirroring `zone_hourly_demand`'s shape (station
  ~ zone).
- FR-3: `algorithms/spatial/`, `algorithms/graph/` gain a London docking-
  station point set consumable by the *same* KD-tree/PageRank
  implementations used for NYC (FR-12 of SPEC-013: algorithms take generic
  areas/centroids, not NYC-specific naming -- this is the first real test of
  that claim).
- FR-4: `models/london_demand/` -- a real demand model trained on
  `london_station_hourly_demand` (start with the EWMA/XGBoost rungs of the
  existing ladder, not the full 4-model ladder -- smallest real model that
  produces a defensible, chronologically-split-validated result).
- FR-5: `backend/services/estimation_service.py` -- the tier-2 mechanism.
  `estimate_demand(population: int, density: float | None) -> PredictionResult`:
  fits a simple ratio/regression of real demand-per-capita from NYC and
  London (the only two real reference points) against population density,
  applies it to a target city's real GeoNames population figure. Returns
  `basis="modeled_estimate"` with a `reason` that states plainly this is a
  2-reference-point scaling, not a validated model -- prefer a wide
  qualitative range (mirroring `journey_predictors.py`'s Ride
  Availability/Surge Risk HIGH/MEDIUM/LOW pattern) over a falsely-precise
  number.
- FR-6: `backend/registry/cities.py` (SPEC-013, resumed) -- `model_status`
  for a city becomes one of `real` / `estimated` / `unavailable`, computed
  from whether a real model artifact exists (`model_registry` seed row with
  `status="active"`) vs. whether GeoNames population data resolves vs.
  neither -- never hand-typed per city.
- FR-7: `backend/routers/cities.py` -- `GET /api/cities/{city_id}/predict/demand`
  routes to the real model (NYC/London), the estimation service (any other
  city with resolvable population), or `CAPABILITY_UNAVAILABLE`, per FR-6.

## Non-Functional Requirements

- **Rule 6 (dbt layering)**: London's staging/marts follow the identical
  one-directional discipline as NYC's -- this is a second proof point for
  the pattern, not a special case.
- **Rule 3 analogue (no leakage) for the estimation service**: the 2-point
  calibration must not be dressed up with confidence intervals or precision
  it doesn't have -- this is explicitly a rough scaling, documented as such
  in the response `reason`, not just the spec.
- **Rule 8 (precompute)**: TfL ingestion and the London model are offline,
  like NYC's; `estimation_service.py`'s regression coefficients are fit
  once at startup from the two real cities' precomputed aggregate
  demand-per-capita, not recomputed per request.

## Data Design

- `london_station_hourly_demand`: `station_id`, `hour`, `day_of_week`,
  `total_trips`, `avg_duration_min`. Grain and shape mirror
  `zone_hourly_demand` deliberately, so the existing algorithm/model code
  can consume it with minimal adaptation.
- Estimation covariate: population (GeoNames, real, already returned by
  `geonames_service.get_children()`/`search_places()`). Density is a
  stretch goal (population / GeoNames-derived land area) if a reliable area
  figure is available; population alone is an acceptable, honestly-labeled
  fallback covariate if not.

## Testing

- `tests/test_london_pipeline.py`: dbt tests on the new staging/mart
  (not_null/accepted_range on trip counts, relationship to the docking-
  station dimension); a correctness test that the London demand model's
  chronological split doesn't leak (rule 3).
- `tests/test_estimation_service.py`: given real NYC+London demand-per-
  capita figures, `estimate_demand()` for a third city with a known
  population returns a plausible-range `modeled_estimate`, never `computed`;
  a city with no resolvable population returns `unavailable`, not a zero or
  a guess.
- Reuse `tests/test_geonames.py`'s existing GeoNames mocking pattern for any
  new tests that touch `geonames_service.get_children()` for population data.

## Risks

1. **TfL Cycle Hire is bike-share, not ride-hailing** -- London's "demand"
   is a different mobility mode than NYC's, not a like-for-like comparison.
   Mitigation: the API response's `source` field always says which dataset
   backs a number (matches rule 22, "every displayed metric must have a
   traceable source"); never implied to be Uber-equivalent.
2. **2-point calibration is statistically weak.** Mitigation: FR-5's
   explicit design choice (qualitative range over false precision) plus a
   documented `reason` string on every estimated response.
3. **TfL data volume/format may need real exploration before FR-1/FR-2 are
   accurate** -- the docs describe the dataset's existence and shape, not
   its exact current file format/size. data-engineer confirms actual
   schema against a real downloaded file before finalizing `stg_london_cycle_journeys.sql`.

## Acceptance Criteria

- [ ] TfL Cycle Hire data ingested into a real DuckDB table; dbt tests pass.
- [ ] `london_station_hourly_demand` mart exists, same shape discipline as
      `zone_hourly_demand`.
- [ ] A real London demand model trained, chronological split verified, real
      metrics recorded (rule 3, rule 5).
- [ ] `estimation_service.py` implemented; returns `modeled_estimate` with
      an honest reason, never `computed`, for any third city with resolvable
      population.
- [ ] `backend/registry/cities.py`'s `model_status` reflects real/estimated/
      unavailable computed from actual artifacts, not hand-typed.
- [ ] NYC's existing endpoints and behavior fully unchanged.
