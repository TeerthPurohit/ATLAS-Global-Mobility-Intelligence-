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
  joined into `zone_hourly_demand`/`london_station_hourly_demand` and used
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

## World Bank PPP (cost-of-living) — `backend/adapters/cost_of_living_worldbank.py`

- **What's real:** each country's real PPP conversion factor (indicator
  `PA.NUS.PPP`), used to scale NYC's real fare-per-mile rate into an honest
  order-of-magnitude fare estimate for any other city.
- **Known reliability gap:** `api.worldbank.org` has been observed to be
  slow/unreachable in some environments (read timeouts even at 20s, while
  the base `worldbank.org` domain resolves quickly). `fetch()` degrades to
  `basis="unavailable"` on any failure — a fare estimate that comes back
  `unavailable` is this adapter being honest, not a bug.

## GTFS transit — `backend/registry/transit.py`, `scripts/ingest_gtfs_feeds.py`

- **What's real:** stop locations from an agency's actual GTFS static feed
  (a `.zip` of CSVs — stdlib `zipfile`/`csv`, no new dependency), ingested
  once per feed (bulk reference data, not a request-time fetch).
- **Explicitly unverified today:** `dbt_project/seeds/gtfs_feeds.csv` ships
  with `feed_url=VERIFY_BEFORE_USE` for both nyc/london — neither has been
  live-verified against MTA's/TfL's current developer pages this pass. The
  ingestion script hard-asserts against that placeholder and refuses to run
  until it's replaced with a real, checked URL. `transit_coverage` honestly
  reports `false` until a feed is both configured *and* ingested.

## Cross-city estimation — `models/cross_city_estimation/estimate.py`

- **What's real:** an N=2 calibration (NYC ride-hailing vs. London
  bike-share, the only two cities with real per-capita mobility data),
  scaled by a target city's real population (and, when available, real
  weather/holiday signals — see below). Always `basis="modeled_estimate"`,
  the `reason` always states the real low/high range implied by the two
  reference rates.
- **Weather/holiday elasticity:** measured, not guessed — real wet-hour and
  holiday demand ratios computed directly against each city's actual
  warehouse. NYC and London *disagree* on the direction of the rain effect
  (ride-hailing demand rises in rain; bike-share demand falls) — a real
  finding, reported honestly via a tightly-clamped near-neutral multiplier
  rather than asserting a direction from two disagreeing points. Both
  cities agree on the holiday effect (demand down), so that multiplier is
  used with more confidence.
- **Explicit gap:** events/concerts as a covariate were considered and cut —
  no verified free, global, $0-budget events data source exists. Not a
  placeholder, not silently dropped — documented in the module itself.
