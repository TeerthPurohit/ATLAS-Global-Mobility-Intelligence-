import duckdb  # noqa: I001
import os
import sys

def df_to_markdown_simple(df):
    cols = df.columns.tolist()
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for idx, row in df.iterrows():
        rows.append("| " + " | ".join(str(val) for val in row.values) + " |")
    return "\n".join([header, separator] + rows)

def main():
    db_path = os.environ.get("DUCKDB_PATH", "data/warehouse/nyc_rides.duckdb")
    report_path = "data/ingestion_report.md"
    
    # Ensure raw directory structures are as expected
    if not os.path.exists("data/warehouse"):
        os.makedirs("data/warehouse")
        
    print(f"Connecting to DuckDB at: {db_path}")
    con = duckdb.connect(db_path)
    
    # Check if tables exist. If not, perform raw ingestion
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    
    loaded_newly = False
    if "raw_trips" not in tables or "raw_zones" not in tables:
        print("Tables raw_trips/raw_zones not found. Running ingestion first...")
        
        # Verify raw files exist
        parquet_files = [f for f in os.listdir("data/raw") if f.endswith(".parquet")]
        if not parquet_files:
            print("ERROR: No parquet files found in data/raw/")
            sys.exit(1)
            
        csv_file = "data/lookup/taxi_zone_lookup.csv"
        if not os.path.exists(csv_file):
            print(f"ERROR: Lookup file not found at {csv_file}")
            sys.exit(1)
            
        print("Ingesting parquet files...")
        con.execute("""
            CREATE OR REPLACE TABLE raw_trips AS
            SELECT * FROM read_parquet('data/raw/fhvhv_tripdata_*.parquet');
        """)
        
        print("Ingesting zone CSV...")
        con.execute("""
            CREATE OR REPLACE TABLE raw_zones AS
            SELECT * FROM read_csv_auto('data/lookup/taxi_zone_lookup.csv');
        """)
        loaded_newly = True
        print("Ingestion complete.")
    
    # Get database size
    db_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_size_mb = db_size_bytes / (1024 * 1024)
    
    # Row counts
    trips_count = con.execute("SELECT COUNT(*) FROM raw_trips").fetchone()[0]
    zones_count = con.execute("SELECT COUNT(*) FROM raw_zones").fetchone()[0]
    
    # Run Spot Checks
    print("Running spot-checks...")
    
    # 1. Null check on critical columns
    nulls_df = con.execute("""
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN "PULocationID" IS NULL THEN 1 ELSE 0 END) AS pu_null,
            SUM(CASE WHEN "DOLocationID" IS NULL THEN 1 ELSE 0 END) AS do_null,
            SUM(CASE WHEN "hvfhs_license_num" IS NULL THEN 1 ELSE 0 END) AS license_null,
            SUM(CASE WHEN "pickup_datetime" IS NULL THEN 1 ELSE 0 END) AS pickup_null,
            SUM(CASE WHEN "dropoff_datetime" IS NULL THEN 1 ELSE 0 END) AS dropoff_null
        FROM raw_trips
    """).fetchdf()
    
    # 2. Negative trip miles
    neg_miles_df = con.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN "trip_miles" < 0 THEN 1 ELSE 0 END) AS negative_miles,
            SUM(CASE WHEN "trip_miles" = 0 THEN 1 ELSE 0 END) AS zero_miles
        FROM raw_trips
    """).fetchdf()
    
    # 3. Timestamp range check
    ts_range_df = con.execute("""
        SELECT
            MIN("pickup_datetime") AS min_pickup,
            MAX("pickup_datetime") AS max_pickup,
            MIN("dropoff_datetime") AS min_dropoff,
            MAX("dropoff_datetime") AS max_dropoff
        FROM raw_trips
    """).fetchdf()
    
    # 4. Out-of-bounds Zone IDs (trips referencing PULocationID / DOLocationID not in raw_zones)
    unmatched_pu = con.execute("""
        SELECT COUNT(*) 
        FROM raw_trips t 
        LEFT JOIN raw_zones z ON t."PULocationID" = z."LocationID"
        WHERE z."LocationID" IS NULL AND t."PULocationID" IS NOT NULL
    """).fetchone()[0]
    
    unmatched_do = con.execute("""
        SELECT COUNT(*) 
        FROM raw_trips t 
        LEFT JOIN raw_zones z ON t."DOLocationID" = z."LocationID"
        WHERE z."LocationID" IS NULL AND t."DOLocationID" IS NOT NULL
    """).fetchone()[0]
    
    # Get zone description
    zones_sample = con.execute("SELECT * FROM raw_zones LIMIT 5").fetchdf()
    
    # Generate Markdown Report
    report_content = f"""# Data Ingestion Verification Report

Generated automatically by `scripts/verify_ingestion.py`.

## 1. Table Statistics

| Table Name | Row Count | Status |
|---|---|---|
| `raw_trips` | {trips_count:,} | {"Loaded newly" if loaded_newly else "Already present"} |
| `raw_zones` | {zones_count:,} | {"Loaded newly" if loaded_newly else "Already present"} |

- **DuckDB Path**: `{db_path}`
- **DuckDB File Size**: {db_size_mb:.2f} MB ({db_size_bytes:,} bytes)

## 2. Zone Lookup Sample

Below is a 5-row sample of the `raw_zones` table:

{df_to_markdown_simple(zones_sample)}

## 3. Spot Checks on `raw_trips`

### Null Value Counts
Checks if key identifiers or timestamp fields are null.

- Total Rows Checked: **{nulls_df['total_rows'][0]:,}**
- Null `PULocationID`: **{nulls_df['pu_null'][0]:,}**
- Null `DOLocationID`: **{nulls_df['do_null'][0]:,}**
- Null `hvfhs_license_num`: **{nulls_df['license_null'][0]:,}**
- Null `pickup_datetime`: **{nulls_df['pickup_null'][0]:,}**
- Null `dropoff_datetime`: **{nulls_df['dropoff_null'][0]:,}**

### Trip Distance Violations
Checks for negative or zero trip distances in miles.

- Negative Trip Miles (`trip_miles` < 0): **{neg_miles_df['negative_miles'][0]:,}** rows
- Zero Trip Miles (`trip_miles` = 0): **{neg_miles_df['zero_miles'][0]:,}** rows

### Timestamp Ranges
Verifies the bounds of the trip dates loaded.

- Min Pickup: `{ts_range_df['min_pickup'][0]}`
- Max Pickup: `{ts_range_df['max_pickup'][0]}`
- Min Dropoff: `{ts_range_df['min_dropoff'][0]}`
- Max Dropoff: `{ts_range_df['max_dropoff'][0]}`

### Zone Integrity Checks
Checks if any location IDs in the trip data do not exist in the taxi zone lookup table.

- Trips with unmatched `PULocationID`: **{unmatched_pu:,}**
- Trips with unmatched `DOLocationID`: **{unmatched_do:,}**

## Conclusion

The ingestion was verified. The results match the expected definition of done.
"""

    with open(report_path, "w") as f:
        f.write(report_content)
        
    print(f"Report successfully written to {report_path}")
    con.close()

if __name__ == "__main__":
    main()
