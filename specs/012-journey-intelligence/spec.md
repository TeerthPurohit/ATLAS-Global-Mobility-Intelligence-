# SPEC-012: Journey Intelligence Engine (Phase 1)

Owner: solo builder · Status: done (Phase 1) · Layer: 5+ (extends Layer 5) ·
Depends on: SPEC-006, SPEC-007, SPEC-008, SPEC-009

## Business Goal

Generalize the NYC-only prediction API (`/predict/demand`, `/predict/fare`)
into a single provider-independent journey endpoint: given pickup,
destination, departure time, and vehicle type, return a full journey report
(fare, ETA, distance, traffic, weather impact, cost breakdown,
availability/surge signals, carbon, confidence, AI explanation). NYC stays
the fully real reference dataset this phase — see ADR-007/ADR-008 for why
the NYC-only zone/borough schema is intentionally untouched, and
`.claude/CLAUDE.md`'s "Read next" table for the roadmap this defers to
(removing the geography assumption, a self-owned data platform, cross-city
intelligence).

## Functional Requirements

- FR-1: `backend/predictors/base.py` — `PredictionResult` (`basis`:
  computed/modeled_estimate/unavailable, `reason` required when not
  computed), `JourneyContext`, `JourneyFeatures`, `VehicleProfile` (ADR-007).
- FR-2: `backend/adapters/` — `DataSourceAdapter` one-method contract;
  real: `weather_openweather.py`, `holidays_nager.py`, `routing_osrm.py`;
  honest stubs: `stubs.py` (traffic/events/airport-arrivals) (ADR-008).
- FR-3: `backend/services/geography_service.py` — `resolve(lat, lon) ->
  zone_id | None`, bbox-gated against NYC's real zone coverage (no snapping
  a non-NYC coordinate to a wrong NYC zone).
- FR-4: `backend/services/vehicle_profiles.py` — loads
  `dbt_project/seeds/vehicle_profiles.csv` (7 classes, emission factors
  cited to EPA's average-passenger-vehicle figure); every vehicle-sensitive
  predictor multiplies by the resolved profile's factors instead of a
  hardcoded per-class branch.
- FR-5: `backend/services/pricing_engine.py` — generalizes `stg_trips.sql`'s
  additive fare formula prospectively: `base_fare` (the trained XGBoost
  model, `computed`) + `vehicle_adjustment` (`computed`, deterministic) +
  `traffic_adjustment`/`weather_adjustment`/`demand_adjustment`
  (`modeled_estimate` — the dollar conversion of a real score into a
  surcharge is a product rule, not a measured fact).
- FR-6: `backend/services/journey_service.py` — `JourneyContext` ->
  `build_features()` -> a fixed predictor sequence (not a generic
  dependency-graph executor — see the design plan's reasoning).
- FR-7: `backend/predictors/journey_predictors.py` — demand, fare_range
  (point estimate ± the fare model's measured test RMSE), carbon
  (deterministic, distance × emission factor), congestion (modeled
  estimate, fuses historical speed + weather), ride_availability / surge_risk
  (modeled estimate, qualitative buckets + reasons, never a fabricated
  driver count or precise multiplier), best_departure_time (sweeps real
  demand predictions across a 6-hour window), confidence (deterministic
  function of the response's own `basis` mix).
- FR-8: `backend/routers/journey.py` — `POST /journey/estimate`.
- FR-9: `rag/journey_narrative.py` — AI Recommendations, reusing
  `generate_insight_docs.py`'s `extract_numbers`/`validate_grounding` so the
  LLM can only restate numbers already in the journey's own prediction
  bundle.
- FR-10: `zone_pair_flows` mart gains `avg_speed_mph` (real, from
  `int_trips_enriched`) — feeds the historical traffic score.

## API Design

| Route | Method | Request | Response |
|---|---|---|---|
| `/journey/estimate` | POST | `pickup_lat`, `pickup_lon`, `dropoff_lat`, `dropoff_lon`, `departure_time`, `vehicle_type` | `distance`, `duration`, `fare`, `fare_range`, `demand`, `carbon_emissions`, `congestion`, `ride_availability`, `surge_risk`, `best_departure_time`, `confidence`, `fare_breakdown` (dict of named terms), `ai_recommendation` — every field a `{value, unit, basis, source, reason}` object. |

Standard REST status codes. A request with a pickup/dropoff outside NYC's
zone coverage or an unrecognized `vehicle_type` still returns 200 — the
affected fields carry `basis="unavailable"` with a `reason`, not a 4xx (the
request itself is well-formed; the platform just doesn't have data for it
yet — see the "global means degrading honestly" design principle).

## Non-Functional Requirements

Every adapter call is a single cacheable point lookup (rule 8) — no request
triggers a warehouse table scan or model retraining. Startup (`journey_service.load()`)
precomputes the citywide baseline speed and zone-name map once, mirroring
`model_service.py`'s artifact-loading pattern.

## Testing

`tests/test_journey.py`: a real NYC pickup/dropoff happy path (every field
present, `basis` always one of the three valid states, `reason` present
whenever not `computed`); a genuinely-outside-NYC-coverage location (Jaipur
coordinates) degrading to `basis="unavailable"` rather than crashing or
silently snapping to a wrong zone; vehicle type changing fare and carbon;
an unrecognized vehicle type returning `unavailable` rather than a silent
default; narrative grounding.

## Acceptance Criteria

- [x] `POST /journey/estimate` implemented and documented above.
- [x] Every response field carries `basis`; `reason` is non-empty whenever
      `basis != "computed"` (enforced at construction by
      `PredictionResult.__post_init__`, not just convention).
- [x] Driver Availability and Surge Probability are never presented as
      measured facts — qualitative buckets + reasons only (ADR-007).
- [x] No paid API is called; unbudgeted sources (traffic/events/airport
      arrivals) return honest stubs (ADR-008).
- [x] `dbt test` passes (22/22) after the `zone_pair_flows` column addition
      and the new `vehicle_profiles` seed.
- [x] 5/5 tests passing in `tests/test_journey.py`; existing
      `tests/test_api.py`/`tests/test_rag.py` unaffected (one pre-existing,
      unrelated failure noted in `.claude/memory.md`'s open questions).

## Explicitly out of scope this phase

NYC-only `Zone`/`zone_id`/`borough` schema generalization (Region/city_id),
a second city, paid traffic/events/airport-arrivals integrations,
self-hosted OSRM (uses the public demo server), Redis/RBAC/CQRS/an
observability stack/microservices (rejected against `.claude/rules.md` rule
7 and `docs/architecture/Infrastructure.md`) — see ADR-007/ADR-008 and
`.claude/memory.md` for the full reasoning.
