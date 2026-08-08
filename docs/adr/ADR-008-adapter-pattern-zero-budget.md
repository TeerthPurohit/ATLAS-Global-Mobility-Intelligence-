# ADR-008: External data-source adapters under a $0 budget

**Status:** Accepted (Journey Intelligence Engine, Phase 1)

## Context

The Journey Intelligence Engine needs weather, holiday, and routing data it
doesn't own. This project has no committed budget for paid APIs
(Traffic: Google/TomTom/HERE; Events: PredictHQ/Ticketmaster; Airport
arrivals: aviationstack/FlightAware), and `docs/architecture/Infrastructure.md`
rules out Redis, a message queue, and a multi-service deployment for what is
a free-tier-hosted solo project.

## Decision

`backend/adapters/base.py` defines one method: `fetch(lat, lon, at) ->
PredictionResult`. Not a five-method interface
(fetch/validate/normalize/enrich/publish) — each adapter makes a single
small HTTP call; validate/normalize are private helpers inside `fetch()`,
and there's no `publish()` because nothing here writes back into the
warehouse (rule 8 — a live weather reading is used at request time and
never backfilled into a mart).

Real implementations, all free: `weather_openweather.py` (OpenWeatherMap
free tier — `basis="unavailable"` if `OPENWEATHER_API_KEY` isn't set, the
expected default state, not an error), `holidays_nager.py` (Nager.Date, free
and global, no key required), `routing_osrm.py` (OSRM's public demo server
by default, `OSRM_URL` overridable to a self-hosted instance for production
load). Honest stubs for the three paid sources
(`stubs.py`: traffic/events/airport-arrivals) return `basis="unavailable"`
with a real reason string, never a `TODO` or a fabricated number — Phase 3
swaps a real implementation in behind the same `fetch()` signature once a
budget exists, with zero changes required upstream in `journey_service.py`
or any predictor.

Every adapter call is a single cacheable point lookup (weather for one
lat/lon bucket, holiday for one date, a route for one origin/destination
pair) — never a table scan, never a mart recompute, never model retraining.
This is the rule-8 boundary stated explicitly: contrast with what rule 8
forbids (reprocessing the 8-10M row raw trips table). Caching is a stdlib
`functools.lru_cache` keyed on a time-bucketed key — no Redis, matching
`Infrastructure.md`.

## Why

Free-tier sources are real, live, external data — not simulated. The
alternative (skip weather/routing/holidays entirely until there's a budget)
would leave the Journey Intelligence Engine unable to demonstrate anything
beyond what the existing `/predict/fare` and `/predict/demand` endpoints
already do. The alternative to honest stubs (fabricating a plausible
traffic number) would violate rule 2 directly.

## Consequences

- Weather can never become a retrainable historical feature on
  OpenWeatherMap's free tier (no 2024 backfill) — it's a capped
  request-time adjustment on top of the historically-trained fare/demand
  predictions, not a new model input. This is a real ceiling, not a
  temporary gap; Phase 3's "own the data platform" is what actually lifts
  it (a paid historical weather API or a self-collected time series).
- OSRM's public demo server is not production-grade (rate limits, no SLA) —
  self-hosting via docker-compose (matching the existing Qdrant service
  pattern) is the documented upgrade path, not done this phase since it
  requires downloading and preprocessing an OSM extract, a genuinely
  separate infra task.
