# Data Ingestion Verification Report

Generated automatically by `scripts/verify_ingestion.py`.

## 1. Table Statistics

| Table Name | Row Count | Status |
|---|---|---|
| `raw_trips` | 8,000,000 | Already present |
| `raw_zones` | 265 | Already present |

- **DuckDB Path**: `data/warehouse/nyc_rides.duckdb`
- **DuckDB File Size**: 387.01 MB (405,811,200 bytes)

## 2. Zone Lookup Sample

Below is a 5-row sample of the `raw_zones` table:

| LocationID | Borough | Zone | service_zone |
| --- | --- | --- | --- |
| 1 | EWR | Newark Airport | EWR |
| 2 | Queens | Jamaica Bay | Boro Zone |
| 3 | Bronx | Allerton/Pelham Gardens | Boro Zone |
| 4 | Manhattan | Alphabet City | Yellow Zone |
| 5 | Staten Island | Arden Heights | Boro Zone |

## 3. Spot Checks on `raw_trips`

### Null Value Counts
Checks if key identifiers or timestamp fields are null.

- Total Rows Checked: **8,000,000**
- Null `PULocationID`: **0.0**
- Null `DOLocationID`: **0.0**
- Null `hvfhs_license_num`: **0.0**
- Null `pickup_datetime`: **0.0**
- Null `dropoff_datetime`: **0.0**

### Trip Distance Violations
Checks for negative or zero trip distances in miles.

- Negative Trip Miles (`trip_miles` < 0): **0.0** rows
- Zero Trip Miles (`trip_miles` = 0): **1,181.0** rows

### Timestamp Ranges
Verifies the bounds of the trip dates loaded.

- Min Pickup: `2024-01-01 00:00:04`
- Max Pickup: `2024-06-30 23:59:59`
- Min Dropoff: `2024-01-01 00:04:17`
- Max Dropoff: `2024-07-01 01:53:54`

### Zone Integrity Checks
Checks if any location IDs in the trip data do not exist in the taxi zone lookup table.

- Trips with unmatched `PULocationID`: **0**
- Trips with unmatched `DOLocationID`: **0**

## Conclusion

The ingestion was verified. The results match the expected definition of done.
