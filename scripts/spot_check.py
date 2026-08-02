import duckdb

con = duckdb.connect("data/warehouse/nyc_rides.duckdb", read_only=True)

print("=== SCHEMA ===")
print(con.execute("DESCRIBE raw_trips").fetchdf().to_string())

print("\n=== NULLS IN PULocationID / DOLocationID ===")
print(con.execute("""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN "PULocationID" IS NULL THEN 1 ELSE 0 END) AS pu_null,
        SUM(CASE WHEN "DOLocationID" IS NULL THEN 1 ELSE 0 END) AS do_null
    FROM raw_trips
""").fetchdf().to_string())

print("\n=== NEGATIVE trip_miles ===")
print(con.execute("""
    SELECT COUNT(*) AS neg_miles
    FROM raw_trips
    WHERE "trip_miles" < 0
""").fetchdf().to_string())

print("\n=== TIMESTAMP RANGE (pickup) ===")
print(con.execute("""
    SELECT
        MIN("pickup_datetime") AS min_pickup,
        MAX("pickup_datetime") AS max_pickup
    FROM raw_trips
""").fetchdf().to_string())

print("\n=== NULLS IN KEY COLUMNS ===")
desc = con.execute("DESCRIBE raw_trips").fetchdf()
cols = desc["column_name"].tolist()
for c in cols:
    cnt = con.execute(f'SELECT SUM(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END) FROM raw_trips').fetchone()[0]
    if cnt > 0:
        print(f"  {c}: {cnt:,} nulls")

con.close()
