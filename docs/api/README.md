# API Reference

The live FastAPI surface (`backend/main.py`). Interactive docs at `/docs`
once the server is running.

Base URL (local dev): `http://localhost:8000`.

## Conventions

- All prediction/journey responses are honest about uncertainty: journey
  fields carry a `basis` of `computed` / `modeled_estimate` / `unavailable`,
  never a fabricated number (ADR-007).
- Legacy routers (`/predict`, `/zones`, `/chat`, `/journey`, platform routes)
  return FastAPI's default `{"detail": "..."}` on error, status 400/404 --
  unchanged, for backward compatibility (SPEC-013 verified this by test).
- The city routers (`/api/cities/*`) use a structured
  `{"error": {"code": ..., "message": ...}}` envelope instead -- see
  [Errors](#errors).

---

## Predictions (legacy, NYC-only, unchanged)

### `GET /predict/demand`

| Param | Type | Required |
|---|---|---|
| `zone_id` | int (TLC LocationID) | yes |
| `hour` | int, 0-23 | yes |
| `day_of_week` | int, 0=Mon .. 6=Sun | yes |

```json
{ "zone_id": 132, "hour": 8, "day_of_week": 1, "predicted_demand": 214.7, "model": "xgboost_demand_v1" }
```

400 if `zone_id` has no demand history.

### `GET /predict/fare`

| Param | Type | Required |
|---|---|---|
| `pickup_zone` | int (TLC LocationID) | yes |
| `dropoff_zone` | int (TLC LocationID) | yes |
| `hour` | int, 0-23 | yes |

```json
{ "pickup_zone": 132, "dropoff_zone": 230, "hour": 8, "predicted_fare": 41.2, "model": "xgboost_fare_v1" }
```

400 if either zone is unknown.

---

## Zones (legacy, unchanged)

`GET /zones` -- all ~265 NYC TLC zones. `GET /zones/{zone_id}` -- single
zone, 400 if unknown.

---

## Journey Intelligence (unchanged)

`POST /journey/estimate`, `GET /journey/history?limit=50`,
`GET /journey/features` -- see `docs/architecture/System-Design.md` and
ADR-007/ADR-008. Every field is a `{value, unit, basis, source, reason}`
object; an out-of-coverage pickup or unrecognized `vehicle_type` still
returns 200 with `basis="unavailable"`, never a fabricated value.

---

## Chat (unchanged contract, gains optional context fields)

### `POST /chat`

```json
{ "question": "What's the average fare from Zone 161 to JFK around 6pm?", "session_id": null, "city_id": null, "area_id": null }
```

`city_id`/`area_id` are optional context fields (SPEC-013 FR-11) -- echoed
back in the response, not yet used to route the RAG pipeline itself (that
pipeline is still NYC-only). Numeric questions no longer let the LLM write
SQL text at all: it emits a `QueryPlan` (`rag/nl_to_sql/query_plan.py`),
validated against the NYC mart schema and compiled deterministically
(SPEC-013 FR-10) -- see `docs/adr/ADR-004-hybrid-rag-nl-to-sql.md`.

```json
{ "answer": "...", "route": "numeric", "sql": "SELECT ...", "session_id": "...", "city_id": null, "area_id": null }
```

`GET /chat/history/{session_id}` (404 if unknown), `WS /chat/stream` --
unchanged.

---

## Platform / Observability (unchanged)

| Route | Returns |
|---|---|
| `GET /health` | DuckDB + Qdrant liveness |
| `GET /dashboard/summary` | Total trips, weighted avg fare, active zone count |
| `GET /warehouse/stats` / `/warehouse/tables` | Row counts, schema |
| `GET /models/metrics` | Demand ladder comparison + fare metadata |
| `GET /marts/zone_hourly_demand` | Hourly demand/fare profile |
| `GET /algorithms/benchmarks` | KD-tree + PageRank real artifacts |
| `GET /pipeline/status` | dbt's own `run_results.json` |
| `GET /insights?limit=20` | Real per-zone insight paragraphs |

---

## Cities (`/api/cities/*`)

City -> Area/Metric/Prediction discovery, backed by
`dbt_project/seeds/{cities,model_registry}.csv` and
`backend/registry/*.py`. Two real cities, NYC and London (ADR-011); every
capability returned is computed from what's actually wired (a real
`model_registry` row, a real `canonical_areas` row), never hand-authored
true/true/true. An unregistered `city_id` is a 404, not a degraded estimate.

| Route | Method | Returns | Errors |
|---|---|---|---|
| `/api/cities` | GET | `CitySearchResponse` (registered cities; optional `q`/`country` filters) | -- |
| `/api/cities/{city_id}` | GET | `City` | `CITY_NOT_FOUND` (404) |
| `/api/cities/{city_id}/capabilities` | GET | `Capabilities` (demand/fare/journey/chat/area_analysis booleans) | `CITY_NOT_FOUND` (404) |
| `/api/cities/{city_id}/areas` | GET | `[Area]` | `CITY_NOT_FOUND` (404) |
| `/api/cities/{city_id}/areas/{area_id}` | GET | `Area` | `AREA_NOT_FOUND` / `CITY_NOT_FOUND` (404) |
| `/api/cities/{city_id}/metrics` | GET | `["demand", "fare", "journey"]` | `CITY_NOT_FOUND` (404) |
| `/api/cities/{city_id}/predict/demand` | POST | `PredictionEnvelope` or `{available:false,...}` | `CITY_NOT_FOUND` (404), `PREDICTION_FAILED` (400) |
| `/api/cities/{city_id}/predict/fare` | POST | `PredictionEnvelope` or `{available:false,...}` | same |
| `/api/cities/{city_id}/forecast?metric=demand&hours=24` | GET | `ForecastEnvelope` or `{available:false,...}` | `CITY_NOT_FOUND` (404), `INVALID_TIME_RANGE` (400) |
| `/api/cities/{city_id}/chat` | POST | `ChatResponse` | `CITY_NOT_FOUND` (404), `CHAT_FAILED` (500) |
| `/api/cities/{city_id}/context` | GET | `CityContextResponse` (geography/weather/calendar/density/routing/demand-shape, each in a provenance envelope) | `CITY_NOT_FOUND` (404) |

`PredictionEnvelope`: `{city_id, area_id, dropoff_area_id, metric,
prediction, model, model_version, generated_at, data_timestamp, source}` --
delegates to the exact same `model_service.py` functions the legacy
`/predict/*` routes call, just provenance-wrapped.

A well-formed request against a real but not-yet-wired capability returns
**200** with `{"available": false, "capability": "...", "reason": "..."}`
(matching `/journey/estimate`'s "data unavailable != 4xx" precedent) --
never a fabricated prediction.

---

## Errors

```json
{ "error": { "code": "CITY_NOT_FOUND", "message": "unknown city_id='xyz'" } }
```

| Code | Typical HTTP | Meaning |
|---|---|---|
| `CITY_NOT_SUPPORTED` / `CITY_NOT_FOUND` | 404 | Unknown `city_id` |
| `COUNTRY_NOT_SUPPORTED` | 404 | Country has no onboarded city |
| `CAPABILITY_UNAVAILABLE` | 200 body | Metric not wired for this city (see above) |
| `MODEL_UNAVAILABLE` | 200 body | Registered model's artifact failed validation at startup |
| `DATA_UNAVAILABLE` | 404 | No data source registered for this city |
| `AREA_NOT_FOUND` | 404 | Unknown `area_id` for a known city |
| `INVALID_TIME_RANGE` | 400 | `/forecast`'s `hours` out of range |
| `PREDICTION_FAILED` | 400 | A well-formed request the underlying model genuinely can't answer (e.g. unknown area_id) |
| `CHAT_FAILED` | 500 | The RAG pipeline itself raised |
| `PLACE_NOT_FOUND` | 404 | Unknown GeoNames place id |
| `INVALID_COORDINATES` | 400 | `lat`/`lng` outside valid range |

Credentials (`OPENAI_API_KEY`, etc.) are backend-only
env vars (`.env`, gitignored) -- never read by the frontend, never echoed in
a response, log, or error message.
