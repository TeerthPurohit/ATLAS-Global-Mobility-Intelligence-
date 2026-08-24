# ADR-013: Collapsing `city_id`

**Status:** Accepted (2026-08-24)

**Follows:** [ADR-012](ADR-012-nyc-only.md), which cut the last second city
and explicitly deferred this: *"Do it as its own change, against a green
suite, or not at all."* This is that change.

## Context

ADR-012 kept the multi-city *shape* on purpose — `city_id` stayed on the
routes, the schemas, the marts and the registry, and `_CITY_ARTIFACTS` and
friends stayed as dicts with one entry. That was the right call for that
commit: mixing an 865-site mechanical rename into the functional London
removal would have made the diff unreviewable.

The cost of leaving it is not correctness, it is honesty of shape. A reader
meets `/api/cities/nyc/capabilities` and reasonably infers there could be an
`/api/cities/boston/capabilities`. There cannot. Every one of those call
sites threaded a parameter with exactly one possible value, and every
one-key dict was keyed by a constant.

## Decision

Remove `city_id` as a **parameter, URL segment, and prop**. Keep it as
**stored data** wherever a row genuinely is identified by city.

**Removed:**

- The `/api/cities/{city_id}` prefix. Fifteen city-scoped endpoints become
  eight: `capabilities`, `areas`, `areas/{area_id}`, `metrics`, `forecast`,
  `profile`, `tariff`, `context`.
- Five of the seven cuts were exact duplicates of un-prefixed routes that
  already existed — `predict/demand`, `predict/fare`, `journey/estimate`,
  `chat`, `zones`. The other two were `GET /api/cities` (a search over one
  row) and `GET /api/cities/{city_id}` (a strict subset of `/api/profile`).
- The `city_id` parameter from every Python signature: `list_areas()`,
  `get_area(area_id)`, `resolve_model(metric)`, `tariff_profiles.get()`,
  `get_capabilities()`, `count_stops_near(lat, lon)`,
  `model_service.predict_demand(...)`, `answer_question(...)`, and the rest.
- The one-entry dicts those parameters indexed: `_CITY_ARTIFACTS`,
  `_CITY_WAREHOUSE_PATHS`, `_CITY_DB_PATH`, `_CITY_SCHEMA`,
  `_CITY_INSIGHT_COLLECTION`, `_ZONE_MODEL_CITIES`, `_CITY_WAREHOUSES`, and
  `model_service`'s per-city momentum/seasonal/month/vintage maps.
- `canonical_areas.city_id` and `model_registry.city_id` — the two columns
  that were constants.
- `backend/routers/cities.py` (now `city.py`), `backend/services/
  city_journey_service.py`, and nine dead `City*` Pydantic schemas.
- `JourneyContext.city_id`, `geography_service.resolve_for_city()` and
  `detect_city_from_coords()`, `journey_service._resolve_city_id()` and its
  `_UNRESOLVED_CITY` sentinel, `pricing_engine._base_fare`'s city branch.
- On the frontend: `resolveCityId()`, the `cityId` prop threaded through
  `CapabilityGate` and all ten journey cards, and the `/city/[city_id]`
  dynamic route (now a static `/city`).

**Kept:**

- `city_id` in **response payloads** (`PredictionEnvelope`, `JourneyEstimate`,
  `ChatResponse`, `WeatherResponse`, …), filled from the `CITY_ID` constant.
  It is real data about the answer, and dropping it would break consumers for
  no gain.
- `city_id` **columns** on `weather_hourly`, `gtfs_feeds`, `gtfs_stops`, the
  `city_tariff_profiles` Postgres table (its primary key) and the prediction
  log. These are stores, not API surfaces; the rows really are per-city, and
  dropping them would force re-ingestion for zero benefit.
- The `cities` seed table itself, and `capability_matrix()` returning `None`
  when it has no row — that is now a deployment fault, surfaced rather than
  papered over with a fabricated profile.

## The seam that replaces it

`backend/registry/__init__.py` holds a single `CITY_ID = "nyc"`. It lives in
the package `__init__` rather than `registry/cities.py` so any module can
import it without a cycle. It is the one place the string is spelled on the
serving path, and it is what the remaining `city_id` columns are filtered by.
Adding a second city means finding every use of that constant and deciding
which should become a parameter again — a greppable list, which the previous
865 scattered sites were not.

On the frontend the analogous seam is `isInCoverage(lat, lon)`, which is what
`resolveCityId()` really was. The id half of that answer was always constant;
the *coverage* half is real, and still gates whether the journey cards render
at all.

## Consequence: two latent bugs surfaced

Neither was caused by this change; both were found because the change made
their code path the only path.

1. `backend/routers/context.py`'s coordinate fallback read
   `profile.get("latitude")`, but `get_city_profile()` nests coordinates
   under `profile["coordinates"]`. The fallback therefore **never fired** —
   `/api/context/weather` without explicit lat/lon always 400'd. With
   `city_id` gone the fallback is the primary path, so it is now correct and
   covered by a test.
2. `JourneyResults.tsx` returned early, above its `useMemo`/`useCapability`
   calls, when no city resolved. That changed the hook count between renders
   whenever a pickup moved in or out of coverage. The guard now sits below
   the hooks.

## What this bought, honestly

Nothing works better. No capability was added, no number changed, no query
got faster. What changed is that the codebase stopped describing a system
that does not exist. That was the whole and only goal, and it is worth
recording that the argument against — a breaking API change with no
behavioural benefit — was accepted as true and overruled on shape alone.

## Alternatives considered

**Leave it.** Rejected, but not unreasonable: the one-entry dicts cost
nothing at runtime, and a second city would want the parameter back. The
counter is that "a second city might arrive" is exactly the speculative
generality ADR-011 and ADR-012 spent two commits removing, and half-removing
it is the worst of both.

**Drop `city_id` from response payloads too.** Rejected as scope creep with
real cost: it breaks every consumer of the JSON for no gain, and unlike a
parameter, a response field carrying `"nyc"` is a true statement.

**Also drop the `city_id` columns from `weather_hourly` / `gtfs_stops` /
`city_tariff_profiles`.** Rejected: those are ingested or externally-stored
data, re-ingesting them buys nothing, and `city_tariff_profiles` lives in
Postgres where a column drop is a migration, not a rebuild.
