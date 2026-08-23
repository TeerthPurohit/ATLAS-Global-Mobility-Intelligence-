# External Data Adapters (the $0-Budget Layer)

Every external data source this platform touches is a real, live, free-tier
API — never simulated data pretending to be live. See
[ADR-008](../adr/ADR-008-adapter-pattern-zero-budget.md) for the full
adapter-pattern rationale; this page is the honest per-source status.

## OSRM routing — `backend/adapters/routing_osrm.py`

- **What's real:** road-network route distance/duration via OSRM's public
  demo server, for any two coordinates on Earth. `basis="computed"`.
- **Ceiling:** the public demo server has no SLA/rate-limit guarantee.
  Self-hosting (docker-compose, an OSM extract) is the documented upgrade
  path, not done — a genuinely separate infra task.
- **Fallback:** haversine straight-line distance, honestly labeled
  `source="haversine"`, never silently swapped in as if it were road
  distance.

## Open-Meteo weather — `backend/adapters/weather_openmeteo.py`

- **What's real:** temperature/precipitation from Open-Meteo's free, keyless
  forecast API (request-time) and historical archive API (backfill). No API
  key, unlike the OpenWeatherMap adapter this replaced.
- **Historical backfill:** `scripts/backfill_weather_openmeteo.py` pulls
  real hourly weather for every date each city's warehouse actually has,
  joined into `zone_hourly_demand` and used
  as a real training feature (see [ADR-008's 2026-08-09 update](../adr/ADR-008-adapter-pattern-zero-budget.md#update-2026-08-09)).
- **Severity score:** a documented, hand-picked formula (precipitation-rate
  dominant, plus a freezing/extreme-heat bump) — not a measured elasticity,
  same honesty as the OpenWeatherMap condition-code table it replaced.

## Nager.Date holidays — `backend/adapters/holidays_nager.py`

- **What's real:** a country's actual public holiday calendar for a given
  year, via the `PublicHolidays/{year}/{country}` endpoint. Global, keyless.
- **Fixed bug:** an earlier version called `IsTodayPublicHoliday`, which
  always checks the server's real *current* date regardless of what
  historical date was requested — silently wrong for anything but literally
  today. Corrected to fetch the real year's holiday list and check
  membership.

## GTFS transit — `backend/registry/transit.py`, `scripts/ingest_gtfs_feeds.py`

- **What's real:** stop locations from an agency's actual GTFS static feed
  (a `.zip` of CSVs — stdlib `zipfile`/`csv`, no new dependency), ingested
  once per feed (bulk reference data, not a request-time fetch).
- **Explicitly unverified today:** `dbt_project/seeds/gtfs_feeds.csv` ships
  with `feed_url=VERIFY_BEFORE_USE` for nyc — it has not been
  live-verified against MTA's/TfL's current developer pages this pass. The
  ingestion script hard-asserts against that placeholder and refuses to run
  until it's replaced with a real, checked URL. `transit_coverage` honestly
  reports `false` until a feed is both configured *and* ingested.

