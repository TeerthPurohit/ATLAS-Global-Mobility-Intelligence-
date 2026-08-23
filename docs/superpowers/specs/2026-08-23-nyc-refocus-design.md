# Retreat from global coverage to NYC + London

**Date:** 2026-08-23
**Status:** Approved, ready for implementation
**Supersedes in practice:** SPEC-013 (global mobility domain model), SPEC-016
(WorldMove grid), ADR-007, ADR-008's global framing, and
`docs/superpowers/plans/2026-08-09-global-city-registry.md`

## Why

Three reasons, all confirmed by the user:

1. **The global data is not trustworthy.** WorldMove population and
   `country_code` are unreliable at the raw `.npy` source (not a pipeline
   bug — see `memory/project_worldmove_population_unreliable.md`). 72% of
   the 517 tariff profiles were duplicate LLM templates
   (`memory/project_tariff_data_quality_fix.md`). The platform was
   presenting modeled-from-nothing numbers for 519 cities alongside NYC's
   real, measured ones.
2. **Scope outran quality.** Breadth work crowded out depth on the two
   cities that have real data.
3. **It does not present well.** The world map + tier taxonomy
   (OBSERVED/TRANSFER/NONE) is a UI built on the weakest data in the repo.

Cutting global is not a retreat from the engineering bar in
`.claude/rules.md` — it is that bar applied. Rule 2 (no fabricated
metrics) and rule 1 (SQL > algorithm > model > LLM) are exactly what the
global layer was straining against.

## What survives

**NYC and London only.** Both are real reference implementations with
honestly-sourced data, real dbt models, and real trained models:

- NYC: HVFHV trip data, XGBoost/EWMA/Linear/LSTM demand ladder, fare
  model, 265 TLC zones, full RAG tier.
- London: Santander Cycles, XGBoost demand model, station-level insight
  docs, full RAG tier.

## Non-goals

- Rewriting the NYC-only zone/borough geography assumption in the dbt
  marts. That deferral stands.
- Deleting the historical record. Superseded specs and ADRs get a
  supersede note, not `rm`. A reversed decision that is documented is
  worth more than one that is erased.

---

## Phase 1 — Redirect the `get_city_profile` seam

Everything global funnels through one function:
`global_geography_service.get_city_profile(city_id)`, called from 9
modules. `backend/registry/cities.py` already does the honest version for
the real 2-row `cities` table (it computes `capabilities` and
`model_status` from live `model_registry` rows rather than trusting a
seed). This phase points every caller at `cities_registry` and
reconciles the returned shape.

Callers to redirect:

- `backend/routers/cities.py`
- `backend/routers/context.py`
- `backend/services/city_journey_service.py`
- `backend/services/context_orchestrator.py`
- `backend/services/estimation_service.py`
- `backend/services/journey_service.py`
- `backend/services/prediction_service.py`
- `backend/services/rag_service.py`
- `backend/services/tariff_enrichment.py` (deleted in phase 2; redirect
  is not needed, listed for completeness)

`estimation_service.py` must be read before editing — it is used by the
NYC journey path too, so its global-only branches are identified during
this phase rather than assumed.

**Verify:** `pytest tests/test_registry.py tests/test_prediction_service.py tests/test_journey.py tests/test_estimation_service.py`

## Phase 2 — Delete backend global code

Delete:

| File | LOC | Reason |
|---|---:|---|
| `backend/services/global_geography_service.py` | 390 | WorldMove tier/population/confidence |
| `backend/services/geonames_service.py` | — | external GeoNames adapter, global place browse only |
| `backend/services/google_places_service.py` | — | same |
| `backend/services/tariff_enrichment.py` | 356 | on-demand LLM tariff invention for unknown cities |
| `backend/registry/global_cities.py` | 60 | the 524-row table |
| `backend/registry/countries.py` | 63 | reads `global_cities`; 2 countries need no registry |
| `backend/routers/countries.py` | — | unmount |
| `backend/routers/geography.py` | ~320 | all 8 endpoints are global place-browse |

Safe to delete `geography.py`: the frontend's `AddressSearch` geocodes
via Nominatim in-browser and never calls it.

Edit:

- `backend/main.py` — drop `global_cities_registry` / `countries_registry`
  startup loads and the 2 router mounts.
- `backend/routers/cities.py` — drop global search/list/tier endpoints and
  the 2 tariff-enrichment endpoints; keep profile/zones/tariff.
- `backend/registry/cities.py` — drop its `global_cities` fallback branch.
- `backend/services/context_orchestrator.py` — its hardcoded
  `"source": "weather_openweather"` string is wrong (the code imports
  `weather_openmeteo`); fix to `weather_openmeteo`.
- `backend/schemas.py` — drop tariff-enrichment frame schemas.

**Verify:** `uvicorn backend.main:app` boots clean; `pytest tests/test_api.py`

## Phase 3 — Prune tests

Delete: `test_build_global_cities.py`, `test_global_cities_registry.py`,
`test_global_cities_table.py`, `test_global_geography.py`,
`test_global_transfer_missing_worldmove.py`,
`test_global_transfer_no_leakage.py`,
`test_global_transfer_no_transfer_labels.py`,
`test_cross_city_estimation.py`, `test_cross_city_calibration_eval.py`.

Edit: `test_api.py`, `test_registry.py`, `test_prediction_service.py`,
`test_fare_provenance_and_capabilities.py`, `test_geography_generalized.py`.

**Verify:** full `pytest` green.

## Phase 4 — dbt

Delete models: `stg_worldmove_cities.sql`, `stg_worldmove_grid.sql`,
`int_worldmove_city_hourly.sql`, `worldmove_area_hourly_momentum.sql`,
`worldmove_city_hourly_shape.sql`.

Edit `canonical_areas.sql`: drop the WorldMove `UNION ALL` branch. This
takes the mart from **154,871 rows to ~1,065** (265 NYC zones + London
stations) — the other 153,800 were WorldMove grid cells.

**Verify:** `dbt build` green; `pytest tests/test_dbt_marts.py`.

## Phase 4b — Data purge

Runs **after** phase 4's dbt rebuild is green, so nothing is deleted
while a model still depends on it. Everything below is gitignored
(`data/raw/*`, `*.duckdb`) — no history rewrite, just disk.

**Raw files (~3.6 GB):**

- `data/raw/worldmove_traj/` — 3.4 GB
- `data/raw/Uber-movement-bangalore-dataset-master.wge8Y7gW.zip.part` — 189 MB
- `data/raw/worldmove_grid/` — 8.4 MB
- `data/raw/worldmove_data/` — 2.7 MB
- `data/raw/worldpop/` — 364 KB

**Warehouse tables to drop (~16.1M rows):** `worldmove_cell_flows` (6.4M),
`worldmove_cell_halfhour` (6.1M), `worldmove_area_hourly_momentum` (3.2M),
`worldmove_city_grid` (154k), `worldmove_city_hourly_shape` (88k),
`int_worldmove_city_hourly` (12.5k), `worldmove_city` (522),
`worldmove_city_population` (522), `global_cities` (523),
`city_tariff_profiles` (1,192 — stale DuckDB mirror; Postgres is the
source of truth per `tariff_profiles.py`).

**Correction found during execution:** `countries` (250 rows) must NOT be
dropped. It is a static ISO reference seed and the FK target for
`cities.country_code`'s relationships test — `dbt build` correctly
re-seeds it. Only `backend/registry/countries.py` and the country routes
go.

**Postgres:** delete all `city_tariff_profiles` rows except `nyc` and
`london` (517 → 2).

**Reclaiming disk:** DuckDB `DROP TABLE` frees blocks for reuse but does
**not** shrink the file. After the drops, `EXPORT DATABASE` to a fresh
file and swap. Keep the original `.duckdb` aside until the swap verifies,
then remove it.

## Phase 5 — Models and scripts

Delete `models/global_transfer/` and `models/cross_city_estimation/` —
the cold-start transfer ladder exists only to serve unmodeled cities;
NYC and London both have real trained models.

**Check before touching:** `models/eta/` and `models/congestion/` — not
yet verified as NYC-real vs global-synthetic. Verify in this phase.

Delete 11 scripts: `download_worldmove.py`, `load_worldmove_mobility.py`,
`load_worldmove_to_duckdb.py`, `build_global_cities.py`,
`geocode_global_cities.py`, `generate_tariff_profile.py`,
`generate_tariff_resumable.py`, `backfill_tariff_extras.py`,
`find_cities_needing_tariff_validation.py`, `validate_tariff_city.py`,
`migrate_tariff_profiles_to_postgres.py`.

**Verify:** full `pytest` green.

## Phase 6 — Frontend

Delete:

- `app/(world)/country/[code]/` and `components/country/`
- `components/world/WorldMap.tsx`, `components/world/SearchBar.tsx`
- `components/capability/TierBadge.tsx` (OBSERVED/TRANSFER/NONE is a
  WorldMove concept)
- `lib/api.ts`: `getCountries`, `searchCities`, `Country` /
  `CitySearch*` types, `streamTariffEnrichment` and its 3 frame types

Rewrite:

- `app/(world)/page.tsx` — NYC hero. Keep the full-bleed `100dvh` shell
  and the GSAP entrance; replace the globe with an NYC zone map and the
  three tier-cards with real content (top demand zones, model metrics).
- `app/(world)/city/[city_id]/` — **keep the route**, restricted to
  `nyc` / `london`. It is the only place `AppContext.selectedCity` is
  set, and `/analyst` reads that to scope chat to the right city;
  deleting it would silently default every chat question to NYC's
  schema. Add a two-city switcher to `NavBar` that sets `selectedCity`
  directly.
- `NavBar.tsx` — drop `/country` path matching, add the switcher.

Untouched: `/journey`, `/compare`, `/insights`, `/analyst`, `/analytics`,
`/history`, `/settings`, `components/journey/*`, `components/ui/*`.

Note: `/compare` is **vehicle-class** comparison (bike/sedan/SUV for one
journey), not city-vs-city. It is not a global feature and needs no
change.

**Verify:** `npm run build` and `npm run lint` clean.

## Phase 7 — NYC zone geometry + map hero

The repo has **no zone polygons** — `data/lookup/` holds centroids only
(`zone_centroids.csv`), and there is no GeoJSON anywhere. `data/raw/`
does contain `taxi_zones.zip` (1 MB, the TLC shapefile).

Add a one-time script converting `taxi_zones.zip` to a simplified
GeoJSON (~500 KB) checked into `data/lookup/`. Conversion needs
`geopandas` as a **dev-only** dependency — it goes in
`requirements.txt`, never `requirements-backend.txt`.

Then build the choropleth: 263 zone polygons shaded by predicted demand.

**Verify:** dev server renders the map with all zones.

## Phase 8 — Dead weight sweep

Independent of the global cut. Found by AST import-reachability analysis
from real entry points (`backend/main.py`, all tests, every file with a
`__main__` guard), not by the stale graphify graph.

Delete:

| Path | Why |
|---|---|
| `backend/adapters/base.py` | `DataSourceAdapter` Protocol, zero importers |
| `backend/adapters/stubs.py` | `fetch_traffic` has zero callers |
| `backend/adapters/weather_openweather.py` | superseded by `weather_openmeteo.py` |
| `backend/datasources/base.py` | `MobilityDataSource` Protocol, zero importers |
| `scripts/cleanup_phase3.py` | one-time script, hardcoded absolute path, **clears directories** |
| `scripts/spot_check.py` | ad-hoc EDA scratch |
| `backend;C` `data;C` `models;C` `rag;C` `dbt_project;C` | empty untracked junk dirs |
| `components/magic/{BorderBeam,ShimmerButton,SpotlightCard}.tsx` | zero imports |
| `frontend/` (React+Vite) | superseded by `frontend-web/`, absent from docker-compose, stale since 2026-08-09 |
| `infra/cdk/cdk.out/` | build output committed to git — untrack and gitignore |
| `site/` | mkdocs build output on disk |

**Explicitly kept** (flagged by the analysis, verified live):
`backend/__init__.py` (package marker), `scripts/load_raw_to_duckdb.py`
(the NYC ingestion entry point named in CLAUDE.md — orphaned only
because it lacks a `__main__` guard), `infra/cdk/{app,stack}.py` (real
CDK deploy, ADR-009).

**Also flagged, needs a decision:** `data/raw/fhvhv_tripdata_2026-03(1).*.parquet.part`
and `2026-04(1).*.parquet.part` — 371 MB of abandoned partial NYC
downloads whose complete counterparts sit in the same folder. Not global,
so not swept automatically.

## Phase 9 — Docs

Rewrite the mission (it currently *promises* global coverage):
`.claude/CLAUDE.md` (mission paragraph + Layer 5 row + the `/frontend`
commands), `.claude/memory.md`, `README.md`, `docs/api/README.md`,
`docs/getting-started/README.md`.

Add **ADR-011 "Retreat from global coverage to NYC + London"** recording
the reversal and its three reasons. Note: `backend/services/tariff_profiles.py`
already cites "ADR-011" in its docstring, but `docs/adr/` stops at 010 —
that reference is dangling and gets fixed to point at the real ADR.

Mark superseded (do not delete): `specs/013-global-mobility-domain-model/`,
`specs/015-second-real-city-and-estimation/`, `ADR-007`, `ADR-008`,
`docs/superpowers/plans/2026-08-09-global-city-registry.md`.

Regenerate `graphify-out/` (currently 2 commits stale, built at
`5add14f`) and update `memory.md` per the standing instruction.

## Success criteria

1. `pytest` green with no global test files remaining.
2. `dbt build` green; `canonical_areas` has ~1,065 rows, all `nyc` or `london`.
3. `uvicorn backend.main:app` boots; no route mentions countries or geography.
4. `grep -ri "worldmove\|global_cities" backend/ rag/ models/ dbt_project/`
   returns nothing outside superseded specs and ADR-011.
5. `npm run build` clean; `/` renders the NYC zone map.
6. DuckDB warehouse contains no `worldmove_*`, `global_cities`, or
   `countries` table, and the file has actually shrunk.
7. The AST orphan scan reports only the explicitly-kept files.
