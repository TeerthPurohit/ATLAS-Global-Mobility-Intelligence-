# Data

## Source

NYC TLC **High Volume For-Hire Vehicle (HVFHV)** trip records -- Uber, Lyft,
Via, Juno (`hvfhs_license_num` codes HV0002/HV0003/HV0004/HV0005). Not
yellow/green taxi: no native `fare_amount`, fares are derived from
`base_passenger_fare + tolls + bcf + sales_tax + congestion_surcharge +
airport_fee + tips` (see `dbt_project/models/staging/stg_trips.sql`).

Three disjoint monthly blocks, **January, March, and June 2024** (~8-10M
rows) -- February/April/May are not in the dataset. Any chronological split
(rule 3, ADR-003) accounts for this rather than trusting a row-count
fraction to land in the right place; see `models/fare_prediction/
train_fare_xgb.py` for the pattern (train+val on earlier blocks, the most
recent complete block held out whole as test).

`scripts/load_raw_to_duckdb.py` loads the raw parquet + the official TLC
taxi zone lookup into `data/warehouse/nyc_rides.duckdb`.

## Transformation (dbt)

Strict one-directional layering (rule 6): `staging` (cast/rename/drop
obviously broken rows only) -> `intermediate` (`int_trips_enriched.sql`,
joins + derived columns) -> `marts` (aggregated, what everything downstream
reads).

| Mart | Grain | Used by |
|---|---|---|
| `zone_hourly_demand` | pickup zone x hour x date | demand model training, `/predict/demand`, `/api/cities/{id}/forecast` |
| `zone_fare_stats` | pickup x dropoff zone pair | fare model features |
| `zone_pair_flows` | pickup x dropoff zone pair x date | PageRank hub graph, journey historical traffic/duration |
| `canonical_areas` | one row per NYC TLC zone (SPEC-013) | `backend/services/geography_service.py`'s `list_areas`/`get_area`, `backend/datasources/nyc_tlc.py` |

Every mart has `dbt test` coverage (`not_null`/`accepted_range` on the
columns that matter, plus a relationship test back to the zone dimension) --
see `dbt_project/models/*/schema.yml`.

## Registries (SPEC-013)

`dbt_project/seeds/{countries,cities,model_registry}.csv` -- dimension-sized
reference tables (rule 8: loaded once at backend startup, not a table-scan
concern), queried by `backend/registry/*.py`. One real city (`nyc`) this
phase; a second city joins by adding rows here, no code changes to the
registry query modules.

## Reference data (seeds)

`taxi_zone_lookup.csv` (official TLC zone/borough lookup), `zone_centroids.csv`
(real lat/lon centroids, EPSG:2263 -> EPSG:4326, used by the KD-tree and
`canonical_areas.sql`), `vehicle_profiles.csv` (per-vehicle-class pricing/
carbon/availability factors, ADR-007).
