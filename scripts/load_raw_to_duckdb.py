import duckdb
import os

con = duckdb.connect(os.environ.get("DUCKDB_PATH", "data/warehouse/nyc_rides.duckdb"))

con.execute("""
    CREATE OR REPLACE VIEW raw_trips AS
    SELECT * FROM read_parquet('data/raw/fhvhv_tripdata_*.parquet', union_by_name=true);
""")

con.execute("""
    CREATE OR REPLACE TABLE raw_zones AS
    SELECT * FROM read_csv_auto('data/lookup/taxi_zone_lookup.csv');
""")

row_count = con.execute("SELECT COUNT(*) FROM raw_trips").fetchone()
zone_count = con.execute("SELECT COUNT(*) FROM raw_zones").fetchone()

print(f"raw_trips: {row_count[0]:,} rows")
print(f"raw_zones: {zone_count[0]:,} rows")
