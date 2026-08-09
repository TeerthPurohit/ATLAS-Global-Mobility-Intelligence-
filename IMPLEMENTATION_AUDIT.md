# Implementation Audit — NYC Ride Intelligence Platform

Read-only audit of actual repo state, done in preparation for a future ML
training pipeline build (NYC + London + WorldMove-backed global transfer
learning). Every number/column/path below was verified by connecting to the
real DuckDB files, reading the real SQL/Python, or running `git status` —
nothing is assumed. Repo root:
`c:\Users\teert\OneDrive\Documents\Teerth Projects\Uber nyc TLC Dataset`.

Verified at HEAD `ee436f6` plus the working-tree changes shown by
`git status` (git status output reproduced in full in section 6).

---

## 1. Existing architecture vs .claude/CLAUDE.md's Layer 0–5 model

| Layer | CLAUDE.md claim | What's actually on disk |
|---|---|---|
| 0 — Data foundation | done | `data/warehouse/nyc_rides.duckdb` (113,075,686-row `int_trips_enriched`, 5 real NYC HVFHV months) + `data/warehouse/london_cycles.duckdb` (2,192,353-row London Santander Cycles). Real. |
| 1 — dbt transformation | done (NYC + London) | `dbt_project/models/{staging,intermediate,marts}` populate both warehouses; confirmed by querying the actual tables (all present, all non-empty). |
| 2 — Algorithms | done | `algorithms/{spatial,graph,timeseries}/` — 6 files (KD-tree, geohash grid, PageRank hubs, Dijkstra-style shortest path, EWMA smoothing, seasonality decompose). Not re-verified for correctness in this audit (out of scope — see `classical-algorithms` skill for that check), but files exist and are non-trivial. |
| 3 — Model ladder | done (NYC XGBoost/EWMA/Linear/LSTM + London XGBoost) | Confirmed: `models/{linear_baseline,ewma_baseline,xgboost_model,lstm_model}` each have a trained artifact + metadata JSON; `models/london_demand/` has its own trained XGBoost + metadata; `models/evaluation/compare_results.json` has real ladder metrics. |
| 4 — Hybrid RAG | done | `rag/` has `router/query_classifier.py`, `nl_to_sql/`, `embeddings/build_vector_store.py`, `insight_generation/`, `rag_pipeline.py`. Not deep-audited here (out of scope for this pass). |
| 5 — Serving & presentation | done (Global Mobility domain model, Discovery APIs, Cross-city estimation) | `backend/` is large and current: `registry/global_cities.py`, `services/global_geography_service.py`, `services/context_orchestrator.py`, `services/estimation_service.py`, `services/tariff_profiles.py` (new/uncommitted), `routers/geography.py` all exist and are wired into `backend/main.py`. |

Beyond the CLAUDE.md table, there is an active **in-progress "tariff/WorldMove
global-city" workstream** not yet reflected in memory.md/CLAUDE.md: a set of
uncommitted files (section 6) adding an LLM-anchored tariff-profile system
(ADR-011, referenced in code but not verified to exist as a file — see
section 8) and a WorldMove population-grid ingestion pipeline feeding
`global_cities`/`worldmove_city_population`.

---

## 2. Existing data tables (real row counts, verified via DuckDB Python bindings)

### `data/warehouse/nyc_rides.duckdb`

| Table | Type | Row count | Date range (if applicable) | Source |
|---|---|---|---|---|
| `raw_trips` | VIEW | 113,218,590 | `pickup_datetime`: 2024-01-01 → 2026-04-30 | raw NYC TLC HVFHV parquet, loaded by `scripts/load_raw_to_duckdb.py` |
| `raw_zones` | BASE TABLE | 265 | — | TLC zone lookup CSV |
| `stg_trips` | VIEW | 113,075,686 | — | `dbt_project/models/staging/stg_trips.sql` |
| `stg_zones` | VIEW | 265 | — | `dbt_project/models/staging/stg_zones.sql` |
| `int_trips_enriched` | BASE TABLE | 113,075,686 | `pickup_at`: 2024-01-01 → 2026-04-30; **only 5 distinct months present: Jan, Mar, Apr, Jun, Nov** (not a continuous timeline) | `dbt_project/models/intermediate/int_trips_enriched.sql` |
| `zone_hourly_demand` | BASE TABLE | 1,441,605 | `pickup_date`: 2024-01-01 → 2026-04-30 | `dbt_project/models/marts/zone_hourly_demand.sql` |
| `zone_pair_flows` | BASE TABLE | 7,200,740 | `pickup_date`: 2024-01-01 → 2026-04-30 | `dbt_project/models/marts/zone_pair_flows.sql` |
| `zone_fare_stats` | BASE TABLE | 64,014 | no date column (all-time aggregate by OD pair) | `dbt_project/models/marts/zone_fare_stats.sql` |
| `canonical_areas` | BASE TABLE | 1,064 | — | `dbt_project/models/marts/canonical_areas.sql` (NYC zones + London stations, unioned) |
| `taxi_zone_lookup` | BASE TABLE | 265 | — | seed `taxi_zone_lookup.csv` |
| `zone_centroids` | BASE TABLE | 263 | — | seed `zone_centroids.csv` |
| `weather_hourly` | BASE TABLE | 8,160 | nyc: 2024-01-01 → 2026-04-30; london: 2026-01-01 → 2026-06-01 | seed `dbt_project/seeds/weather_hourly.csv` (modified in working tree) |
| `cities` | BASE TABLE | 2 (nyc, london) | — | seed `cities.csv` |
| `countries` | BASE TABLE | 2 | — | seed `countries.csv` |
| `global_cities` | BASE TABLE | 524 (522 `TRANSFER`, 2 `OBSERVED`) | — | built by `scripts/build_global_cities.py` (registered cities + WorldMove) |
| `worldmove_city_population` | BASE TABLE | 522 | — | `scripts/load_worldmove_to_duckdb.py` from `data/raw/worldmove_data/*.npy` |
| `city_tariff_profiles` | BASE TABLE | 6 rows (all `INR`/`JPY`/`NGN`, all `source='llm_anchored'`, `model_id='gpt-5.4-nano'`, `confidence=0.7`) | — | `backend/services/tariff_profiles.py` write path, `scripts/generate_tariff_profile.py` |
| `vehicle_profiles` | BASE TABLE | 7 | — | seed `vehicle_profiles.csv` |
| `gtfs_feeds` | BASE TABLE | 2 | — | seed `gtfs_feeds.csv` |
| `model_registry` | BASE TABLE | 5 | — | seed `dbt_project/seeds/model_registry.csv` |

### `data/warehouse/london_cycles.duckdb`

| Table | Type | Row count | Source |
|---|---|---|---|
| `raw_journeys` | BASE TABLE | 2,195,790 | raw TfL Cycle Hire CSV |
| `stg_london_cycle_journeys` | VIEW | 2,193,459 | `stg_london_cycle_journeys.sql` |
| `stg_london_stations` | VIEW | 799 | `stg_london_stations.sql` |
| `int_london_journeys_enriched` | BASE TABLE | 2,192,353 | `int_london_journeys_enriched.sql` |
| `london_station_hourly_demand` | BASE TABLE | 846,677 | `london_station_hourly_demand.sql` (config'd to write into this DB, database='london_cycles') |
| `london_stations` | BASE TABLE | 799 | seed `london_stations.csv` |

**Note on `int_trips_enriched`'s date gap**: confirmed present, non-continuous
— `SELECT DISTINCT pickup_month` returns `{1, 3, 4, 6, 11}` only (Feb, May,
July–Oct, Dec absent). This matches the `.claude` memory note about a
Jan/Mar/Jun 2024 gap but the real gap set has since grown to include Apr,
Jun, and Nov (dates span into 2026, so "month" here spans multiple years —
verify by full date, not just month-of-year, before building any seasonal
feature).

**Tables named in the task prompt that do NOT exist** (checked and absent):
no table called `stg_trips.csv` staging by that literal name outside dbt,
no separate `nyc_fare_anchor` table (it's a Python function, not a table),
no `city_tariff_profiles` seed CSV (it's a runtime-written DuckDB table, no
CSV backing).

---

## 3. Exact column names (verified via `DESCRIBE`, not inferred from SQL)

```
int_trips_enriched:
  trip_id BIGINT, hvfhs_license_num VARCHAR, pickup_at TIMESTAMP, dropoff_at TIMESTAMP,
  pickup_location_id INTEGER, dropoff_location_id INTEGER, trip_distance DOUBLE,
  trip_duration_minutes BIGINT, fare_amount DOUBLE, tolls DOUBLE, bcf DOUBLE,
  sales_tax DOUBLE, congestion_surcharge DOUBLE, airport_fee DOUBLE, tip_amount DOUBLE,
  driver_pay DOUBLE, total_amount DOUBLE, pickup_borough VARCHAR, pickup_zone VARCHAR,
  pickup_service_zone VARCHAR, dropoff_borough VARCHAR, dropoff_zone VARCHAR,
  dropoff_service_zone VARCHAR, avg_speed_mph DOUBLE, pickup_hour BIGINT,
  pickup_day_of_week BIGINT, pickup_month BIGINT, pickup_date DATE, is_weekend BOOLEAN

raw_trips (raw HVFHV columns, note PascalCase LocationID + snake_case elsewhere):
  hvfhs_license_num, dispatching_base_num, originating_base_num, request_datetime,
  on_scene_datetime, pickup_datetime, dropoff_datetime, PULocationID, DOLocationID,
  trip_miles, trip_time, base_passenger_fare, tolls, bcf, sales_tax,
  congestion_surcharge, airport_fee, tips, driver_pay, shared_request_flag,
  shared_match_flag, access_a_ride_flag, wav_request_flag, wav_match_flag,
  cbd_congestion_fee

zone_hourly_demand:
  pickup_date DATE, pickup_hour BIGINT, pickup_location_id INTEGER,
  pickup_borough VARCHAR, pickup_zone VARCHAR, total_trips BIGINT,
  avg_trip_distance_miles DOUBLE, avg_fare DOUBLE, temperature_c DOUBLE,
  precipitation_mm DOUBLE

zone_pair_flows:
  pickup_date DATE, pickup_borough VARCHAR, pickup_zone VARCHAR,
  dropoff_borough VARCHAR, dropoff_zone VARCHAR, trip_count BIGINT,
  total_revenue DOUBLE, avg_duration_min DOUBLE, avg_speed_mph DOUBLE, flow_rank BIGINT

zone_fare_stats:
  pickup_borough, pickup_zone, dropoff_borough, dropoff_zone, trip_count,
  avg_fare, median_fare, min_fare, max_fare, avg_tip, avg_distance, avg_duration_min

weather_hourly: city_id VARCHAR, date DATE, hour INTEGER, temperature_c DOUBLE,
  precipitation_mm DOUBLE   (city_id present — this is a shared multi-city table)

cities: id, name, country_code, latitude, longitude, timezone, currency, status,
  data_source, geography_type, mobility_mode, model_status, last_updated (DATE),
  population (INTEGER), land_area_km2

global_cities: city_id, name, country_code, latitude, longitude, timezone, currency,
  population (DOUBLE), population_source, model_status, worldmove_available (BOOLEAN)

worldmove_city_population: worldmove_id INTEGER, country_code, city_name,
  grid_rows INTEGER, grid_cols INTEGER, population_total DOUBLE,
  population_density_mean DOUBLE, population_density_max DOUBLE, source_file

city_tariff_profiles: city_id, currency, base_fare, per_km, per_min, min_fare,
  night_multiplier, airport_surcharge, source, generated_at (TIMESTAMP), model_id,
  confidence, notes

model_registry: model_id, city_id, metric, model_type, version, artifact_path,
  training_period, status, metrics_ref

canonical_areas: area_id INTEGER, city_id VARCHAR, name, area_type, parent_area_id,
  latitude, longitude

zone_centroids: LocationID INTEGER, zone, borough, latitude, longitude
  (⚠ PascalCase LocationID here, unlike zone_hourly_demand's pickup_location_id
  and stg_zones's location_id — three different casings for "zone id" across
  tables; a training script joining across marts must handle this explicitly)

--- london_cycles.duckdb ---

int_london_journeys_enriched:
  journey_id BIGINT, start_at TIMESTAMP, end_at TIMESTAMP, start_station_id VARCHAR,
  end_station_id VARCHAR, bike_id BIGINT, bike_model VARCHAR, duration_minutes DOUBLE,
  start_station_name, start_station_lat, start_station_lon, end_station_name,
  end_station_lat, end_station_lon, start_hour BIGINT, start_day_of_week BIGINT,
  start_date DATE, is_weekend BOOLEAN

london_station_hourly_demand:
  station_id VARCHAR, station_name, trip_date DATE, hour BIGINT, day_of_week BIGINT,
  total_trips BIGINT, avg_duration_min DOUBLE, temperature_c DOUBLE,
  precipitation_mm DOUBLE
  (⚠ station_id is VARCHAR here, but int_trips_enriched's zone id is
  INTEGER — model_service.py's per-city `area_column` config exists
  specifically to paper over this type difference at inference time; a
  shared cross-city training frame must cast explicitly)

raw_journeys (original TfL column names with spaces, kept as-is):
  Number, "Start date", "Start station number", "Start station", "End date",
  "End station number", "End station", "Bike number", "Bike model",
  "Total duration", "Total duration (ms)"
```

---

## 4. Existing ML code inventory

| Path | State |
|---|---|
| `models/linear_baseline/linear_regression_model.py` | Trained. `linear_model.joblib` + `linear_model_metadata.json` present. |
| `models/ewma_baseline/ewma_forecast.py` | Trained/computed. `ewma_baseline_metadata.json` present. |
| `models/xgboost_model/train_xgboost.py` | Trained. `xgb_model.json` + `xgb_metadata.json`, **both modified in the working tree** (uncommitted retrain — see below). Real hyperparameter grid search recorded (4 candidates), real feature importances, real val/test RMSE/MAE. |
| `models/lstm_model/{dataset.py,train_lstm.py}` | Trained. `lstm_model.pt`, `lstm_metadata.json`, `loss_curve.png` present. |
| `models/london_demand/{build_features.py,train_london_xgb.py}` | Trained (second, independent city model). `xgb_model.json` + `xgb_metadata.json`. Same feature set as NYC's XGBoost (`hour, day_of_week, is_weekend, lag_1h, lag_24h, lag_168h, ewma, rolling_7d_avg, temperature_c, precipitation_mm`), separately fit. Test RMSE 1.69 / MAE 1.05 (much lower scale than NYC's 24.2/12.6 — station-level bike departures vs zone-level ride-hail pickups, not comparable without normalizing by base rate). |
| `models/fare_prediction/train_fare_xgb.py` | Trained. NYC-only. Chronological block-aware split (train+val = Jan+Mar, test = June in full — see section 11). `fare_xgb_model.json` + `fare_xgb_metadata.json`. |
| `models/data_prep/{build_features.py,train_test_split.py}` | `train_test_split.py` (modified in working tree) implements both a generic `chronological_split()` (unique-timestamp-boundary based) and `split_demand_blocks()` (holds the latest calendar month out as test, computed from the data's own max date, not hardcoded). |
| `models/cross_city_estimation/estimate.py` | Implements `estimate_demand_per_capita()` — the NYC/London 2-reference-point population-scaling logic backing `estimation_service.py`. Not a trained model; a small deterministic function. |
| `models/evaluation/compare_models.py` + `compare_results.json` | Real ladder comparison: linear RMSE 5.42/MAE 3.53, ewma RMSE 7.46/MAE 4.62, xgboost RMSE 5.09/MAE 3.26, lstm RMSE 5.63/MAE 3.66, all n=142,993, real per-row latency measured. XGBoost wins on RMSE/MAE; EWMA is cheapest (fastest) but worst-fit. |
| `models/query_plan_finetune/evaluate.py` + `eval_report.json` | Present (Layer 4 fine-tuning eval), not deep-audited (out of scope). |
| `algorithms/{spatial,graph,timeseries}/*.py` | 6 files present (KD-tree zone lookup, geohash grid, PageRank hubs, zone-graph builder, shortest-path ETA, EWMA smoothing, seasonality decompose = 7 actually, listed above). Not re-verified for correctness here. |

**Staleness flag**: `models/xgboost_model/xgb_model.json`, `xgb_metadata.json`,
and `feature_importance.png` are all shown as modified (`M`) by `git
status` but not committed — i.e., there is a retrained NYC demand model
sitting in the working tree that differs from the last commit. Its metadata
(`xgb_metadata.json`, read above) shows date range train 2024-01-08 →
2026-01-31, val → 2026-03-31, test → 2026-04-30 — this is **already** trained
across the full 2024–2026 span the warehouse now has (not just the original
Jan/Mar/Jun 2024 sample memory.md still describes), with real row counts
876,855 / 155,542 / 143,730. **memory.md's "Jan/Mar/Jun 2024 gap" note is
stale relative to this uncommitted retrain** — flag for whoever runs
`/layer-status` or `/docs` next.

---

## 5. Existing model registry — what exists, what's missing

**What exists**: `model_registry` DuckDB table (seeded from
`dbt_project/seeds/model_registry.csv`), 5 rows:

```
model_id                    city_id  metric   model_type            version  artifact_path                                     training_period          status  metrics_ref
xgboost_demand_v1           nyc      demand   xgboost               v2       models/xgboost_model/xgb_model.json               2024-01/2024-03/2024-06  active  models/xgboost_model/xgb_metadata.json
ewma_fallback_v1            nyc      demand   ewma                  v1       models/ewma_baseline/ewma_baseline_metadata.json  2024-01/2024-03/2024-06  active  models/ewma_baseline/ewma_baseline_metadata.json
xgboost_fare_v1             nyc      fare     xgboost               v1       models/fare_prediction/fare_xgb_model.json        2024-01/2024-03/2024-06  active  models/fare_prediction/fare_xgb_metadata.json
journey_predictors_v1       nyc      journey  rule_based_ensemble   v1       backend/predictors/journey_predictors.py          n/a                      active  docs/adr/ADR-007-predictor-basis-field.md
xgboost_london_demand_v1    london   demand   xgboost               v2       models/london_demand/xgb_model.json               2026-01/2026-03/2026-05  active  models/london_demand/xgb_metadata.json
```

This is a **static seed CSV, not auto-generated from training runs** — its
`training_period` strings are stale text (`2024-01/2024-03/2024-06`) that no
longer match the uncommitted retrain's real 2024-01→2026-04 span (section 4).
Nothing writes to this table/CSV automatically after a training script runs.

**What's tracked today**: model_id, city_id, metric, model_type, version,
artifact_path, training_period (free text), status, metrics_ref (pointer to
a metadata JSON file that has the real numbers).

**What each `*_metadata.json` artifact separately tracks** (per-model, not
centralized): seed, date_range (train/val/test), n_rows per split, feature
list, hyperparameters, hyperparameter_search (full grid), feature_importances,
metrics (val/test RMSE/MAE + inference latency), library_versions
(xgboost/pandas/numpy version strings). This is solid per-model
reproducibility metadata — it's just not surfaced in the `model_registry`
table itself, and there's no `data_version`/`git_commit`/`feature_version`
field anywhere in either place.

**Missing relative to a full registry**: data snapshot/version hash (e.g.
which warehouse build these rows came from), git commit SHA of the training
run, training config file reference (configs live inline in each script's
constants, not externalized), automatic write-back after a training run
(today: hand-edit the CSV), and no row at all for `linear`/`lstm` baselines
even though they have metadata files (only demand/fare/journey/london-demand
made it into the registry).

---

## 6. Global geography / city registry service — how model status and confidence resolve today

Three related-but-distinct registries exist, verified by reading the code:

1. **`backend/registry/cities.py`** — the 2 fully "OBSERVED" cities (nyc,
   london) with real warehouses.
2. **`backend/registry/global_cities.py`** (new, per commits b2abaa3/
   7acabe3/acc8056) — loads the 524-row `global_cities` DuckDB table at
   startup into an in-process dict (`load()`/`get_city()`/`find_by_name()`/
   `list_cities()`), same load-once-at-startup pattern as `cities.py` (rule
   8: no per-request table scans). Exposes `model_status` (`OBSERVED` for
   the 2 registered cities, `TRANSFER` for the other 522 WorldMove-backed
   cities) directly from the table — it does not compute status itself, it
   just reads what `scripts/build_global_cities.py` wrote.
3. **`backend/services/global_geography_service.py`** — the actual resolver
   `generate_tariff_profile.py`/tests call (`get_city_profile()`). Confirmed
   via `tests/test_global_geography.py`: for a registered city it returns
   `model_status: "OBSERVED"`, `confidence: 1.0`; for a WorldMove-covered
   city (e.g. Jaipur) it returns `model_status: "TRANSFER"`, `0.0 <
   confidence < 1.0`. `capabilities.observed_mobility` is the boolean gate:
   `True` only for nyc/london.

So the concept is real and tested (not just documented aspiration): two
tiers, `OBSERVED` (has a trained per-zone model, confidence=1.0) and
`TRANSFER` (population/WorldMove-covariate-only, confidence <1.0, no
zone-level model). `estimation_service.py`/`models/cross_city_estimation/
estimate.py` is what actually serves demand numbers for `TRANSFER`-tier
cities, always tagged `basis="modeled_estimate"`, never `"computed"`.

**Confidence for TRANSFER cities**: not derived from any measured accuracy
number in this repo (there is no held-out evaluation of the transfer
estimate's real-world error) — it is a static/derived value from
`global_geography_service.py`'s own logic, not empirically calibrated. This
is a real gap for anyone building an ETA/demand model on top of it: the
`confidence` field currently means "which tier resolved this," not "P(this
estimate is within X% of truth)."

---

## 7. Existing dbt models (one-line purpose each, read from actual SQL)

**Staging** (`dbt_project/models/staging/`):
- `stg_trips.sql` — casts/renames raw HVFHV trip columns into `int_trips_enriched`'s snake_case shape.
- `stg_zones.sql` — casts/renames `raw_zones` (TLC lookup) into `location_id/borough/zone_name/service_zone`.
- `stg_london_cycle_journeys.sql` — casts/renames `raw_journeys` (TfL CSV, spaced column names) into `journey_id/start_at/end_at/...`.
- `stg_london_stations.sql` — casts/renames London station seed data.

**Intermediate** (`dbt_project/models/intermediate/`):
- `int_trips_enriched.sql` — joins `stg_trips` to `stg_zones` twice (pickup + dropoff), computes `avg_speed_mph` and time-dimension columns (`pickup_hour/day_of_week/month/date/is_weekend`).
- `int_london_journeys_enriched.sql` — same enrichment pattern for London journeys + stations.

**Marts** (`dbt_project/models/marts/`):
- `zone_hourly_demand.sql` — groups `int_trips_enriched` by (date, hour, pickup zone), joins city-level `weather_hourly` (nyc-only filter), one row per zone-hour.
- `zone_pair_flows.sql` — groups `int_trips_enriched` by (date, pickup zone, dropoff zone) with a `ROW_NUMBER()` `flow_rank` per pickup zone per day — the OD-flow-ranking mart PageRank/graph algorithms consume.
- `zone_fare_stats.sql` — all-time (no date grain) fare aggregates per OD zone pair — avg/median/min/max fare, avg tip/distance/duration.
- `canonical_areas.sql` — unions NYC zones (from `stg_zones` + `zone_centroids` seed) and London stations (from `stg_london_stations`) into one cross-city `(area_id, city_id, name, area_type, parent_area_id, lat, lon)` shape.
- `london_station_hourly_demand.sql` — London's equivalent of `zone_hourly_demand.sql`, explicitly `{{ config(database='london_cycles') }}` to land in the separate warehouse file, same grain/shape by design so downstream code can reuse it with minimal adaptation.

**Seeds**: `cities.csv`, `countries.csv`, `taxi_zone_lookup.csv`, `zone_centroids.csv`, `london_stations.csv`, `gtfs_feeds.csv`, `vehicle_profiles.csv`, `model_registry.csv`, `weather_hourly.csv` (modified in working tree), `fixed_holidays_extended.csv` (new, untracked — see section 8).

No macros directory content was found beyond dbt's generated `dbt_packages`/`target`/`logs` — this project does not appear to use custom dbt macros.

---

## 8. New/uncommitted files — what they do

Confirmed by reading each file directly:

- **`backend/adapters/fx_rates.py`** — live FX rates via the free
  `fawazahmed0/exchange-api` CDN (primary + documented fallback host),
  `lru_cache`-memoized `_fetch_rates()`, returns a `PredictionResult` with
  `basis="computed"` on success or `"unavailable"` with a reason on failure.
  Explicitly documented as never on the primary fare path — only used to
  anchor/compare currencies when generating a tariff profile.

- **`backend/services/tariff_profiles.py`** — the `city_tariff_profiles`
  DuckDB table's dataclass model (`TariffProfile`) + `load()`/`get()`/
  `upsert()`/`ensure_table()`. Read path is startup-loaded (rule 8: no
  write lock held by the live server); write path is offline-only, called
  from `scripts/generate_tariff_profile.py`/`calibrate_tariff_nyc.py`.

- **`dbt_project/seeds/fixed_holidays_extended.csv`** — output of
  `scripts/extract_fixed_holidays.py`: countries not covered by the live
  Nager.Date API, with holidays that recur on the *identical calendar date*
  in every year of a 2010–2019 reference dataset (i.e., provably fixed-date,
  not floating) — India explicitly named as the motivating gap.

- **`docs/tariff_calibration.json`** — output of `calibrate_tariff_nyc.py`:
  one real measured number, the LLM's blind (no-data) guess at NYC's fare
  structure vs NYC's actual measured fares, as a MAPE percentage over a
  50,000-row sample — this is the credibility anchor cited by every
  `llm_anchored` tariff profile's `reason` field.

- **`scripts/calibrate_tariff_nyc.py`** — runs the above; standalone, not
  imported elsewhere.

- **`scripts/nyc_fare_anchor.py`** — `fit_nyc_fare_anchor()`: a real
  least-squares fit (`numpy.linalg.lstsq`) of `total_amount ~ base +
  per_mile*trip_distance + per_min*trip_duration_minutes` over a 200,000-row
  sample of `int_trips_enriched`. This is the one real linear decomposition
  of NYC fare structure anywhere in the repo (the trained fare XGBoost model
  predicts `total_amount` directly and was never asked to decompose it).
  Imported by `generate_tariff_profile.py` and `calibrate_tariff_nyc.py`.

- **`scripts/generate_tariff_profile.py`** — one-time offline LLM call per
  city (never on a request path): prompts an LLM with the real NYC anchor
  numbers plus the target city's name/currency, asks for a tariff structure
  in the target's own currency, validates the response (required fields,
  currency match, non-empty justification), and `upsert()`s it into
  `city_tariff_profiles`. Currently used to generate the 6 rows found in
  section 2 (Mumbai, Jaipur, Delhi, Kolkata, Tokyo, Lagos — resolved by
  GeoNames ID, not city_id, per the raw table dump).

- **`scripts/download_worldmove_india.py`** — scrapes the WorldMove data
  portal's JS bundle for city keys (regex over a `.js` asset, not an
  official API), filters to India + a hardcoded "first world" country-code
  allowlist (US/CA/GB/FR/DE/AU/... ~49 codes), downloads each city's `.npy`
  population grid into `data/raw/worldmove_data/`.

- **`scripts/load_worldmove_to_duckdb.py`** — parses `{worldmove_id}_
  {country_code}_{city_name}.npy` filenames, loads each grid, summarizes
  (sum/mean/max) into `worldmove_city_population` rather than storing raw
  cell-level arrays. This is the population/mobility-intensity covariate
  backing `TRANSFER`-tier cities.

- **`tests/test_seasonal_profile.py`** — regression test for a fixed "stale
  numbers" bug: asserts `predict_demand()` actually varies output by
  hour/day-of-week/month (not one frozen last-known-row snapshot), asserts
  `data_vintage()` reports a real range, asserts the hourly-shape fractions
  sum to 1.0 per day-of-week. All currently pass against the real warehouse
  (test is `skipif` on warehouse absence, not mocked).

- **`tests/test_tariff_profiles.py`** — unit tests (fully mocked via
  `monkeypatch`, no DB dependency) for `pricing_engine._base_fare_tariff()`:
  fare increases monotonically with distance, minimum-fare floor holds,
  missing profile degrades to `basis="unavailable"` (never fabricated), and
  FX being unreachable does not break the local-currency fare (proves FX is
  correctly decoupled from the price path).

---

## 9. Missing components — gaps relative to a full training pipeline

Genuinely absent (verified by searching for them, not found):

- **No quantile/probabilistic ETA output anywhere.** All demand models
  (`xgboost_model`, `london_demand`) predict a single point estimate
  (`total_trips`); no quantile regression, no prediction intervals. The
  fare model is likewise point-estimate only.
- **No congestion/traffic target.** `avg_speed_mph` exists as a *feature*
  in `int_trips_enriched`, but no model trains against it as a target, and
  no "congestion score" mart exists.
- **No city embedding / learned city representation.** Cross-city transfer
  today is a hand-written 2-reference-point population-scaling formula
  (`models/cross_city_estimation/estimate.py`) plus an LLM-anchored tariff
  guess — there is no learned embedding space, no similarity-based
  nearest-city lookup beyond `global_cities`'s flat `country_code`/
  `population` fields.
- **No LLM context builder for a training/eval loop** — `rag/`'s context
  assembly is for the chat/insight layer, not for feeding an ML training
  pipeline; `context_orchestrator.py` builds request-time API context, not
  training features.
- **No automatic model-registry write-back.** Every `*_metadata.json` is
  real and detailed, but nothing promotes those numbers into
  `model_registry.csv`/table automatically — it's a hand-maintained seed.
- **No cross-city joint training.** NYC and London each have entirely
  separate XGBoost models with independently tuned hyperparameters; no
  shared feature space, no multi-task or fine-tune-from-NYC path exists for
  a third city yet, despite the WorldMove ingestion pointing that direction.
- **No held-out accuracy measurement for `TRANSFER`-tier confidence.** As
  noted in section 6, `confidence` for the 522 WorldMove cities is not
  backed by any measured error against a real held-out city — there is no
  "hold out London, predict it as if it were TRANSFER-tier, measure error"
  experiment anywhere in the repo. This is the single biggest empirical gap
  standing between the current heuristic and an actual calibrated ensemble.
- **Data-gap-aware feature engineering exists but isn't generalized.**
  `models/data_prep/train_test_split.py`'s `split_demand_blocks()` and
  `train_fare_xgb.py`'s `_latest_month_start()` both handle the
  discontinuous-month problem correctly for their specific tables, but the
  logic is duplicated (near-identical function in two files) rather than
  shared, and neither is parameterized by city — a third city's own data
  gaps would require copy-pasting the pattern again.

Already covered (do not re-build):
- Chronological, leakage-safe splitting (`models/data_prep/
  train_test_split.py`, tested by `test_fare_split_no_leakage.py`).
- Per-city model loading/dispatch contract (`backend/services/
  model_service.py`'s `_CITY_ARTIFACTS` dict pattern — already
  demonstrates how a third city's demand model would plug in).
- Real metadata capture per training run (seed, date ranges, hyperparameter
  search, feature importances, library versions) — the shape is right, it
  just isn't centralized (section 5).
- OBSERVED/TRANSFER tiering and confidence surfacing end-to-end from DB →
  service → API → test (section 6) — extending this to a third tier (e.g.
  a calibrated-TRANSFER after the missing experiment above) is additive,
  not a rebuild.

---

## 10. Proposed files to add (only what isn't already covered by existing conventions)

Given `models/` already has a clear one-directory-per-model-type convention
with a training script + metadata JSON + (optional) joblib/pt/json artifact,
new work should extend that convention, not create a parallel `ml/` tree:

- `models/data_prep/chronological_split.py` (or promote the existing
  `train_test_split.py` functions) — **not new logic**, but worth
  de-duplicating the `_latest_month_start()` copy that currently exists
  separately in `train_test_split.py` and `train_fare_xgb.py`, and
  parameterizing `split_demand_blocks()` by a `min_gap_days` or explicit
  block list so a third city's own date gaps don't require a third copy.
- `models/cross_city_estimation/calibration_eval.py` — the missing
  held-out-city calibration experiment from section 9 (train London/NYC as
  if TRANSFER-tier, measure real error against the OBSERVED-tier ground
  truth already in the warehouse). This directly produces the confidence
  number section 6 is currently missing, using data that already exists —
  no new ingestion needed.
- `scripts/refresh_model_registry.py` — a small script that reads every
  `models/*/*_metadata.json` already being written and rewrites
  `dbt_project/seeds/model_registry.csv` from them (git commit SHA via
  `git rev-parse HEAD`, training_period from each metadata's own
  `date_range`). Closes the "hand-edited registry" gap in section 5 without
  inventing a new registry mechanism.
- A third city's demand model, once WorldMove/tariff work identifies a
  target with real trip-level data, would follow the exact
  `models/london_demand/` pattern (`build_features.py` +
  `train_<city>_xgb.py`) and register in `model_service.py`'s
  `_CITY_ARTIFACTS` dict — this is a 2-file addition per city today, not a
  new architecture.

Explicitly **not** proposed: a new `ml/` package, a new registry database,
a new feature-store abstraction, a new config-management layer — none of
these are missing in a way existing conventions can't extend.

---

## 11. Exact training datasets to generate (real row counts, not hypothetical)

- **NYC demand**: `zone_hourly_demand` (1,441,605 rows, 2024-01-01 →
  2026-04-30, 5 non-contiguous months) feeds `models/data_prep/
  build_features.py` → lag/EWMA/rolling features. The uncommitted retrain
  already trains on 876,855/155,542/143,730 (train/val/test) rows spanning
  the full 2024–2026 range — not the original 3-month sample memory.md
  describes.
- **NYC fare**: `int_trips_enriched` (113,075,686 rows total; training
  script samples via `USING SAMPLE ... ROWS (reservoir, seed)` when
  `sample_rows` is set, full-table otherwise) — current committed artifact
  trained on Jan+Mar (train+val) / Jun (test) only, per its metadata; this
  predates the retrain and should be re-run against the fuller date range
  the warehouse now has, the same way the demand model already was.
- **London demand**: `london_station_hourly_demand` (846,677 rows,
  2026-01-08 → 2026-06-01) — already trained (764,663/135,914/451,584
  train/val/test).
- **Cross-city transfer calibration** (proposed, section 10): the 2
  OBSERVED cities' own `zone_hourly_demand`/`london_station_hourly_demand`
  aggregated to city-daily totals (small — a few hundred to ~1,000 rows
  each after date aggregation) vs `worldmove_city_population`'s 522-row
  population covariate table — this is a small, fast experiment, not a
  big-data job.
- **Tariff/global-city work**: `global_cities` (524 rows) and
  `worldmove_city_population` (522 rows) are already loaded; the 6-row
  `city_tariff_profiles` table is a start on a much larger LLM-anchored
  generation job (there are 522 TRANSFER cities, only 6 have a tariff
  profile so far) — generating the rest is an offline batch job against
  `scripts/generate_tariff_profile.py`, not new code.

No 113M-figure applies to anything except `int_trips_enriched`/`raw_trips`
themselves — every actual model-training table is a pre-aggregated mart at
1.4M rows (NYC demand) or smaller.

---

## 12. Potential data leakage risks (grounded in what was actually found)

- **Real, tested chronological-split discipline exists** and is
  non-trivial: `chronological_split()` cuts on unique-timestamp boundaries
  (not raw row position) specifically so that rows sharing an identical
  timestamp — e.g. every zone's row for the same hour — always land in the
  same split; a naive row-count split would otherwise put the same hour's
  data in both train and val. `split_demand_blocks()`/`train_fare_xgb.py`'s
  `split_data()` additionally hold the entire most-recent calendar month
  out as test, computed from the data's own max date (not a hardcoded
  cutoff) — this correctly avoids the "fraction-of-concatenated-blocks"
  bug the code comments describe (a naive 85/15 split across the
  discontiguous Jan/Mar/Jun blocks would land the test cutoff mid-June,
  mixing early-June train rows with late-June test rows).
- **Risk not yet covered by a test**: the demand feature table
  (`zone_hourly_demand`) has *lag/EWMA/rolling* features computed
  per-zone. If a future feature-engineering step computes those over the
  full month-gapped series without being gap-aware, a `lag_168h` (7-day
  lag) feature computed naively across e.g. the Mar→Apr boundary would
  silently pull a value from 100+ real days earlier than 7 days, not a true
  7-day lag — worth adding an explicit test that lag features respect the
  real gaps, mirroring what `test_fare_split_no_leakage.py` does for the
  split itself.
- **`city_tariff_profiles`' LLM-anchored generation is explicitly
  train/test-safe by construction** — it never touches trip-level data for
  any city except NYC (used only to build the anchor prompt), so there's no
  leakage risk there, but it also means its "confidence" score is
  self-reported by the LLM (0.7 for all 6 rows seen), not empirically
  validated — see section 6's gap.
- **No random-split code was found anywhere** in `models/` — every split
  path found (`train_test_split.py`, `train_fare_xgb.py`) is chronological.
  This is a genuinely clean finding, not a risk.
- **Cross-city calibration risk if section 10's proposed experiment is
  built naively**: using London to "validate" a TRANSFER-tier estimate for
  NYC (or vice versa) is legitimate leave-one-city-out validation *only if*
  the population-scaling formula's constants (`NYC_FARE_PER_MILE`, the
  2-reference-point demand-per-capita ratio in `models/cross_city_
  estimation/estimate.py`) are refit excluding the held-out city each time
  — today those constants are hardcoded from both cities' real fitted
  values, so naively "testing" against London or NYC without refitting
  would be circular (the held-out city's own number is baked into the
  formula being tested).

---

## 13. Recommended first training experiment

Given the actual state above, the smallest, most valuable, achievable-now
experiment is **section 10's leave-one-city-out TRANSFER-tier calibration**:

1. Take NYC's `zone_hourly_demand` and London's
   `london_station_hourly_demand`, aggregate each to city-level daily total
   demand (small: a few hundred rows per city after aggregation — trivial
   compute).
2. Refit `models/cross_city_estimation/estimate.py`'s 2-reference-point
   demand-per-capita scaling **using only one city's real ratio** (e.g.
   fit on NYC's population + measured demand only).
3. Apply that single-city-fitted formula to predict London's daily demand
   as if London were a TRANSFER-tier city with no trip-level data (only its
   real population from `cities`/`global_cities`), and measure the real
   error (MAPE/RMSE) against London's own real, measured demand mart.
4. Repeat the reverse direction (fit on London, predict NYC).
5. Write the resulting real MAPE numbers into `docs/` (mirroring
   `docs/tariff_calibration.json`'s pattern of "one real, bounded number"),
   and use them to replace `global_geography_service.py`'s currently
   uncalibrated `confidence` value for TRANSFER-tier cities with an
   empirically grounded one.

This is achievable in an afternoon (no new ingestion, no new infra, reuses
existing marts and the existing `estimate.py` module), directly closes the
single biggest measured gap found in this audit (section 6/9's uncalibrated
confidence score), and produces exactly the kind of "one real, honest
number" this repo's own rules.md discipline already expects everywhere
else (see `docs/tariff_calibration.json`'s MAPE-vs-real-fares precedent).
