# SPEC-013: Global Mobility Domain Model (Phase 1 — architecture generalization)

> **SUPERSEDED (2026-08-23) by [ADR-011](../../docs/adr/ADR-011-retreat-from-global-coverage.md).**
> The global-coverage layer this describes has been removed: the platform now
> serves only cities with real observed trip data (NYC, London). Kept as a
> record of the decision and why it was reversed, not as a description of the
> current system.

Owner: solo builder · Status: draft · Layer: 5+ (extends Layers 1, 4, 5) ·
Depends on: SPEC-002, SPEC-006, SPEC-007, SPEC-008, SPEC-009, SPEC-012

## Business Goal

Generalize the platform's shape from "NYC Ride Intelligence" to "Global
Mobility Intelligence" — a Country → City → Geography/Area → Metric →
Prediction → Conversation domain model — **without** touching NYC's existing
behavior. NYC becomes the first (and, this phase, only) real entry in a
registry other cities can join later. This picks up work SPEC-012 explicitly
deferred: "the NYC-only `Zone`/`zone_id`/`borough` schema is untouched (no
Region/city_id generalization yet), no second city onboarded... (see
ADR-007/ADR-008)."

Non-goals this phase: onboarding a real second city (no second dataset, no
second trained model), building the LLM city-schema-adapter itself (only its
target interface — the Canonical Mobility Query Plan — is built now, since
there is no second schema yet to adapt to), wiring the `frontend/` app onto
the new endpoints, and anything involving `frontend-web/` (an untracked,
unrelated Next.js scaffold — explicitly out of scope, not touched).

## Functional Requirements

- FR-1: `dbt_project/seeds/countries.csv` (ISO code, name — sovereign states)
  and `dbt_project/seeds/cities.csv` (id, name, country_code, latitude,
  longitude, timezone, currency, status, data_source, geography_type,
  model_status, last_updated) — one real row: `nyc`. Same seed + `schema.yml`
  pattern already established by `vehicle_profiles.csv` (ADR-008).
- FR-2: `dbt_project/seeds/model_registry.csv` — model_id, city_id, metric,
  model_type, version, artifact_path, training_period, status, metrics_ref.
  Catalogs artifacts that already exist (`xgboost_demand_v1`,
  `ewma_fallback_v1`, `xgboost_fare_v1`, journey predictors) — no retraining.
- FR-3: `dbt_project/models/marts/canonical_areas.sql` — generalizes the
  existing NYC zone dimension into `(area_id, city_id='nyc', name,
  area_type='zone', parent_area_id=borough, latitude, longitude)`. Reads from
  the staging zone model, not from a mart, to respect rule 6 (marts don't
  read marts).
- FR-4: `backend/registry/countries.py`, `backend/registry/cities.py`,
  `backend/registry/models.py` — thin query modules over the seeded tables,
  loaded once at startup (rule 8: these are dimension tables, ~195 / 1 /
  handful of rows — trivially small, not a table scan concern). Expose
  `list_countries()`, `get_country(code)`, `list_cities(country_code=None)`,
  `get_city(city_id)`, `get_capabilities(city_id)`, `resolve_model(city_id,
  metric)`.
- FR-5: `backend/services/geography_service.py` (exists, SPEC-012) gains
  `list_areas(city_id)` / `get_area(city_id, area_id)` backed by
  `canonical_areas`. The existing `resolve(lat, lon) -> zone_id` KD-tree
  lookup is unchanged — nearest-neighbor search is a distinct concern from
  listing a city's areas.
- FR-6: `backend/datasources/base.py` — `MobilityDataSource` protocol:
  `get_areas`, `get_demand`, `get_fares`, `get_zone_flows`,
  `get_temporal_metrics`. `backend/datasources/nyc_tlc.py` —
  `NYCTLCDataSource`, thin wrappers over the existing marts via the same
  DuckDB connection pattern `model_service.py`/`platform_service.py` already
  use. `get_trips()` is deliberately **not** part of the live-serving
  protocol (rule 8) — raw trip rows stay dbt/offline-only.
- FR-7: `backend/services/prediction_service.py` — orchestrator: resolve city
  → check capability against the city's row → resolve model via
  `model_registry` → call the **existing, unchanged**
  `model_service.py`/`journey_service.py` functions → wrap the result in a
  provenance envelope (`city_id`, `area_id`, `metric`, `prediction`, `model`,
  `model_version`, `generated_at`, `data_timestamp`, `source`).
- FR-8: `backend/schemas.py` gains an `ErrorCode` enum (`CITY_NOT_SUPPORTED`,
  `CITY_NOT_FOUND`, `COUNTRY_NOT_SUPPORTED`, `CAPABILITY_UNAVAILABLE`,
  `MODEL_UNAVAILABLE`, `DATA_UNAVAILABLE`, `AREA_NOT_FOUND`,
  `INVALID_TIME_RANGE`, `PREDICTION_FAILED`, `CHAT_FAILED`) and an
  `ErrorResponse` schema, surfaced via FastAPI exception handlers.
- FR-9: New routers — `backend/routers/countries.py`
  (`GET /api/countries`, `GET /api/countries/{code}`),
  `backend/routers/cities.py` (`GET /api/countries/{code}/cities`,
  `GET /api/cities/{city_id}`, `GET /api/cities/{city_id}/capabilities`,
  `GET /api/cities/{city_id}/areas`, `GET /api/cities/{city_id}/areas/{area_id}`,
  `GET /api/cities/{city_id}/metrics`), plus city-scoped predict/chat routes
  (`POST /api/cities/{city_id}/predict/demand`, `/predict/fare`,
  `GET /api/cities/{city_id}/forecast`, `POST /api/cities/{city_id}/chat`)
  that delegate to `prediction_service`/`rag_pipeline`. **Every existing
  route (`/predict/demand`, `/predict/fare`, `/zones`, `/chat`,
  `/journey/estimate`, the platform routes) stays mounted, unchanged
  behavior.**
- FR-10: `rag/nl_to_sql/query_plan.py` — a `QueryPlan` schema (`intent`,
  `city_id`, `metric`, `filters` [hour/day/area_id/date_range],
  `aggregation`, `group_by`, `order`, `limit`). `sql_agent.py` is restructured
  so the LLM produces a `QueryPlan` (constrained call) instead of raw SQL
  text; the plan is validated against the resolved city's metric/geography
  profile from the registry, then compiled to SQL deterministically. This is
  the seed of a future multi-city "LLM city adapter" — no second city's
  resolver is built this phase, only NYC's. It also closes the NL-to-SQL
  injection surface (the LLM never emits SQL text anymore).
- FR-11: `ChatRequest`/`ChatResponse` gain optional `city_id`/`area_id`
  context fields; the existing grounding discipline (ADR-004,
  `validate_grounding()`) is unchanged.
- FR-12: Verify (don't rewrite unless proven necessary) that
  `algorithms/{spatial,graph,timeseries}` already operate on generic
  arrays/centroids/flows rather than NYC-specific naming internally.
- FR-13: `docs/` restructured into the full tree from the brief (getting
  started / architecture / data / algorithms / models / api / deployment /
  operations / changelog), populated with real content reflecting what's
  actually implemented. Every new (and existing, where practical) FastAPI
  route gets `summary`/`description`/`tags`/`response_model`/documented error
  responses.
- FR-14: Structured logging (stdlib `logging`, no new infra) for city
  resolution, model resolution, capability checks, and query-plan
  compilation/execution.

## Non-Functional Requirements

- **$0 budget** (ADR-008): no new paid APIs or services.
- **Rule 8 (precompute)**: registries are dimension-table-sized and loaded
  once at startup; no new per-request table scan.
- **Backward compatibility (rule 7 spirit + explicit ask)**: every
  pre-existing endpoint's request/response shape and behavior is unchanged.
  This is verified by test, not just by intent.
- **Solo scope (rule 7)**: no Redis/queue/microservices/multi-tenant auth —
  matches `docs/architecture/Infrastructure.md`.

## Current State

- SPEC-012 (Journey Intelligence Engine) already generalized the
  *prediction* side: `backend/predictors/base.py`'s `PredictionResult` with a
  structural `basis` field, `backend/adapters/` (provider-agnostic external
  data), `vehicle_profiles.py`, `pricing_engine.py`, `journey_service.py`,
  `geography_service.py` (lat/lon → zone_id only, today).
- No City/Country concept exists anywhere in the backend. No area/geography
  abstraction beyond the raw `zone_id`/`Zone` schema. No model registry — 
  `model_service.py` hardcodes artifact paths. No generalized discovery API.
  Chat has no city/area context field.
- `frontend/` is mid-migration (uncommitted TS+Tailwind rewrite, matches the
  Layer 5 audit-fix description in `.claude/memory.md`) — out of scope this
  phase, not touched. `frontend-web/` is an unrelated, untracked, abandoned
  Next.js scaffold — ignored entirely.

## Proposed Design

```
Country registry (dbt seed)          Model registry (dbt seed)
        │                                    │
        ▼                                    ▼
   City registry (dbt seed, 1 real row: nyc) ─┐
        │                                     │
        ▼                                     │
  canonical_areas (dbt mart, wraps zone dim)   │
        │                                     │
        ▼                                     ▼
   backend/registry/*.py  ──────►  prediction_service.py
        │                                │
        ▼                                ▼
  new discovery routers          existing model_service.py /
  (countries, cities,            journey_service.py (UNCHANGED)
  areas, capabilities)                   │
        │                                ▼
        └──────────────►  provenance-wrapped response
```

Key tradeoffs:

- **DB-backed registries (dbt seeds + DuckDB tables) over Python dicts.**
  Matches this repo's existing pattern (`vehicle_profiles.csv`) and rule 1
  (SQL over hardcoded logic) better than an in-memory registry would.
- **Wrapping views over renaming.** `canonical_areas` and any canonical
  metric views are additive dbt models reading from staging/existing marts —
  `zone_hourly_demand`, `zone_fare_stats`, `zone_pair_flows`, and the `Zone`
  Pydantic schema are not renamed or removed (section 12 of the brief is
  explicit about this; also avoids breaking every downstream algorithm/model
  that keys on `zone_id` today).
- **Canonical Mobility Query Plan over direct NL→SQL.** A structured
  intermediate representation the LLM fills in, validated before compilation
  to SQL — safer than an LLM emitting SQL text directly, and the natural seed
  for a future multi-city adapter (a second city's schema resolver plugs into
  the same compilation step later; not built this phase).
- **Capability flags are asserted from what's real, not aspirational.** NYC's
  `capabilities` row is written to match what's actually wired (`demand`,
  `fare`, `journey`, `chat`, `area_analysis` = true; anything not truly
  backed stays false) — this is the mechanism that keeps rule 2 (no
  fabrication) true at the registry level, not just the prediction level.

## Data Design

- `countries` (seed): `iso_code` (PK), `name`. No `supported` column stored —
  derived at query time via a join against `cities` (a country is
  "supported" iff it has ≥1 city row), avoiding a denormalized flag that can
  drift from the city list.
- `cities` (seed): `city_id` (PK), `name`, `country_code` (FK → countries),
  `latitude`, `longitude`, `timezone`, `currency`, `status`, `data_source`,
  `geography_type`, `model_status`, `last_updated`. `capabilities` and
  `metrics` are not seed columns (they'd drift from reality) — computed by
  `backend/registry/cities.py` from what routers/registry entries actually
  exist for that `city_id`.
- `canonical_areas` (dbt mart): `area_id`, `city_id`, `name`, `area_type`,
  `parent_area_id`, `latitude`, `longitude`. Grain: one row per NYC TLC zone
  today. dbt tests: `unique`+`not_null` on `area_id`, `accepted_values` on
  `area_type`, relationship test back to the zone dimension.
- `model_registry` (seed): `model_id` (PK), `city_id`, `metric`,
  `model_type`, `version`, `artifact_path`, `training_period`, `status`,
  `metrics_ref` (path to the existing metrics JSON). `backend/registry/models.py`
  validates `artifact_path` exists at startup; a missing file sets
  `status="unavailable"` rather than crashing or silently serving nothing.

## API Design

| Route | Method | Response | Error cases |
|---|---|---|---|
| `/api/countries` | GET | list of `Country` (name, iso_code, supported, supported_city_count) | — |
| `/api/countries/{code}` | GET | `Country` | `COUNTRY_NOT_SUPPORTED` |
| `/api/countries/{code}/cities` | GET | list of `City` | `COUNTRY_NOT_SUPPORTED` |
| `/api/cities/{city_id}` | GET | `City` | `CITY_NOT_FOUND` |
| `/api/cities/{city_id}/capabilities` | GET | `Capabilities` | `CITY_NOT_FOUND` |
| `/api/cities/{city_id}/areas` | GET | list of `Area` | `CITY_NOT_FOUND` |
| `/api/cities/{city_id}/areas/{area_id}` | GET | `Area` | `AREA_NOT_FOUND` |
| `/api/cities/{city_id}/metrics` | GET | list of available metric names | `CITY_NOT_FOUND` |
| `/api/cities/{city_id}/predict/demand` | POST | provenance-wrapped prediction | `CAPABILITY_UNAVAILABLE`, `MODEL_UNAVAILABLE`, `PREDICTION_FAILED` |
| `/api/cities/{city_id}/predict/fare` | POST | provenance-wrapped prediction | same |
| `/api/cities/{city_id}/forecast` | GET | provenance-wrapped series | `CAPABILITY_UNAVAILABLE`, `INVALID_TIME_RANGE` |
| `/api/cities/{city_id}/chat` | POST | `ChatResponse` | `CHAT_FAILED` |

An unsupported city/capability returns 200 with a structured
`{"available": false, "capability": ..., "reason": ...}` body where the
brief calls for it (section 10), and a proper 404 with `ErrorResponse` for
genuinely missing resources (`CITY_NOT_FOUND`, `AREA_NOT_FOUND`) — matching
the "data unavailable ≠ 4xx for a well-formed request" precedent SPEC-012
already set for `/journey/estimate`.

## Testing

- `tests/test_registry.py`: country/city listing, capability resolution
  matches what's actually wired (no city claims a capability with no backing
  router), unsupported city/country returns the documented error, not a 200
  with fake data.
- `tests/test_geography_generalized.py`: `list_areas("nyc")` returns 265
  rows matching the existing zone count; unknown city_id raises/returns
  `CITY_NOT_FOUND`.
- `tests/test_datasource_nyc.py`: each `NYCTLCDataSource` method returns
  real mart-backed data; `get_trips` is not part of the live protocol.
- `tests/test_prediction_service.py`: capability-gated prediction for a
  supported metric matches direct `model_service` output; an unsupported
  metric/city returns `CAPABILITY_UNAVAILABLE`/`MODEL_UNAVAILABLE`, never a
  fabricated number.
- `tests/test_query_plan.py`: NL question → `QueryPlan` → validator rejects
  a plan referencing a field outside the resolved city's schema; compiled SQL
  matches expected shape for a known question; no path emits raw LLM-authored
  SQL.
- Extend `tests/test_api.py`: one happy-path test per new endpoint, plus an
  explicit backward-compatibility test asserting every pre-existing endpoint
  (`/predict/demand`, `/predict/fare`, `/zones`, `/chat`, `/journey/estimate`)
  still returns the same shape it did before this spec.
- `dbt test` passes for the new seeds/mart (uniqueness, not-null, accepted
  values, relationships).

## Risks

1. **This spans 5+ subsystems (dbt, backend services, routers, RAG,
   docs/OpenAPI) in one spec** — the largest single change this repo has
   made. Mitigation: every piece is additive (new tables, new routers, new
   files); nothing existing is renamed or deleted, so a partial rollout still
   leaves the platform working. Backward-compat tests are the release gate.
2. **Restructuring `sql_agent.py` around a `QueryPlan` could regress today's
   NL-to-SQL answer quality/latency.** Mitigation: keep the existing
   grounding tests green, add plan-specific tests, and if the LLM's
   structured-output call fails, fall back to today's direct-SQL path rather
   than failing the whole chat turn (a `basis`-style honest degrade, not a
   silent regression).
3. **`canonical_areas`/canonical metric views reading from existing marts
   tension with rule 6** ("marts don't read marts"). Mitigation:
   `canonical_areas` reads from the staging zone model, not a mart; any
   canonical metric view is documented explicitly as a thin presentation
   view, not a new mart with business logic, and data-engineer reviews rule
   6 compliance per model before merging.

## Acceptance Criteria

- [ ] `dbt seed` + `dbt run` succeed; `dbt test` passes for `countries`,
      `cities`, `model_registry`, `canonical_areas`.
- [ ] `GET /api/countries`, `/api/countries/{code}`, `/api/countries/{code}/cities`,
      `/api/cities/{city_id}`, `/capabilities`, `/areas`, `/areas/{area_id}`,
      `/metrics` implemented and documented in OpenAPI with tags.
- [ ] City-scoped predict/chat routes implemented, delegating to existing
      model/journey/RAG logic unchanged.
- [ ] Every pre-existing endpoint verified byte-for-byte behavior-identical
      via test.
- [ ] `ErrorCode`/`ErrorResponse` used consistently; no endpoint returns a
      bare 500 for an expected "not supported" case.
- [ ] NYC's registered `capabilities` exactly match what's actually callable
      (verified by test, not hand-authored trust).
- [ ] `rag/nl_to_sql/query_plan.py` in place; NL-to-SQL path no longer lets
      the LLM emit raw SQL text; existing chat tests + new query-plan tests
      pass.
- [ ] `docs/` restructured per the target tree, populated with real content;
      no page describes unimplemented behavior as if it existed.
- [ ] `.claude/memory.md` and `CLAUDE.md`'s layer table updated to reflect
      this phase.
- [ ] No second city, no `frontend/` changes, `frontend-web/` untouched —
      confirmed at review, not just intended.
