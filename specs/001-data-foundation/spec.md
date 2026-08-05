# SPEC-001: Data Foundation

Owner: solo builder · Status: done · Layer: 0 · Depends on: none

## Business Goal

Get 3 months of NYC TLC HVFHV trip data (~8-10M rows) into DuckDB, joined to
the zone lookup, as the single source everything else reads from.

## Functional Requirements

- FR-1: Download 3 months of HVFHV parquet from the TLC trip record page.
- FR-2: Load `taxi_zone_lookup.csv` (zone, borough, service_zone).
- FR-3: `CREATE TABLE AS SELECT * FROM read_parquet(...)` directly into
  DuckDB — no pandas intermediate step for the bulk load.
- FR-4: Verify row count lands in the 8-10M target range.
- FR-5: Spot-check known TLC data issues: nulls in PU/DOLocationID,
  negative trip distances, timestamps outside the expected month range.

## Current State

Done. `scripts/load_raw_to_duckdb.py`, `scripts/verify_ingestion.py`,
`scripts/spot_check.py` exist and have run against
`data/warehouse/nyc_rides.duckdb`. Confirmed source is HVFHV (carrier codes
HV0002=Juno, HV0003=Uber, HV0004=Via, HV0005=Lyft), not yellow/green taxi.

## Testing

`scripts/spot_check.py` / `verify_ingestion.py` cover the FR-5 checks. No
additional test needed — this layer is a one-time load, not logic that can
silently regress.

## Acceptance Criteria

- [x] Raw parquet loaded into DuckDB.
- [x] Zone lookup loaded.
- [x] Row count verified in 8-10M range.
- [x] Known data-quality issues spot-checked.
