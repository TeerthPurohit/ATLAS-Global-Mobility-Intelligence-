# Adding a City

This is the concrete, repeatable process the architecture is actually built
around — not an assertion that it "scales," a checklist you can run. Every
step is additive: a new city never requires touching another city's code
path.

## The bar (ADR-011)

A city is added when it brings **its own real trip records**. There is no
prior-based tier: the previous WorldMove-backed layer that gave any
GeoNames-resolvable place an order-of-magnitude estimate was removed because
its source data wasn't trustworthy enough to present beside measured numbers.
An unregistered `city_id` returns 404.

So there is no "Tier 0". Step 1 below is the first step.

## Step 1 — real observed predictions

To give a city `computed` demand/fare:

1. **Add a row to `dbt_project/seeds/cities.csv`** with real, sourced
   `population`/`land_area_km2`, citing where the numbers came from
   (Census/ONS or equivalent official source — a figure without a citation
   doesn't go in the seed).
2. **Build a dbt staging → intermediate → mart pipeline** for that city's
   real trip-level data, ending in an hourly-demand mart with the same
   column shape as `zone_hourly_demand`/`london_station_hourly_demand`
   (grain: date, hour, area, `total_trips`).
3. **Add rows to `canonical_areas`** for that city (`UNION ALL` into
   `dbt_project/models/marts/canonical_areas.sql`, following the London
   station-import pattern).
4. **Train a demand model** using the existing feature-engineering shape
   (`models/data_prep/build_features.py`/`models/london_demand/
   build_features.py` are the two references — same lag/EWMA/rolling
   features, same weather join at `(date, hour)` grain).
5. **Add a row to `dbt_project/seeds/model_registry.csv`** (`city_id`,
   `metric="demand"`, `status="active"`, real `artifact_path`).
6. **Add a `_CITY_ARTIFACTS` entry in `backend/services/model_service.py`**
   pointing at the new model/warehouse/feature module.
7. **Add a data source** in `backend/datasources/` (mirror
   `london_cycles.py`'s shape) and export it from
   `backend/datasources/__init__.py`.

That's it — `get_capabilities()`, `predict_demand`, `/forecast`, and the
city-scoped journey endpoint all pick this up automatically; none of them
have a per-city branch to edit.

## Step 2 — full chat

1. **Register the warehouse path** in `backend/registry/cities.py`'s
   `_CITY_WAREHOUSE_PATHS` — this alone gives the city the `sql_only` chat
   tier (real SQL against its own marts).
2. **Build a `CityMobilitySchema`** for it (mirror `rag/nl_to_sql/
   london_schema.py` — only declare the metrics/tables that actually exist;
   omit `fare`/`flow` if no such mart exists, exactly like London does).
3. **Register the schema/db path** in `backend/services/rag_service.py`'s
   `_CITY_DB_PATH`/`_CITY_SCHEMA` dicts.
4. *(Optional, for `full_rag`)* Generate an insight-doc corpus for the city
   and add it to `_CITY_HAS_INSIGHT_DOCS` in `backend/registry/cities.py`.

## Step 3 — transit context

1. Find and **verify** the city's real GTFS static feed URL against its
   transit authority's official developer/open-data page.
2. Add a row to `dbt_project/seeds/gtfs_feeds.csv` with the real URL and
   today's date in `last_verified`.
3. Run `scripts/ingest_gtfs_feeds.py` — it refuses to run against the
   `VERIFY_BEFORE_USE` placeholder, so this step only succeeds once step 1
   is real.

## What never changes

No step above touches NYC's or London's code paths, `_require_city`'s
resolution logic, or any router. Every addition is a new seed row, a new
small per-city module, or a new dict entry.
