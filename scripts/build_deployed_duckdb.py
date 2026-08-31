"""Create the read-only DuckDB artifact used by the deployed API.

The local warehouse contains raw and intermediate trip tables that are not
needed by the serving application. Keep this export deterministic and never
overwrite the source warehouse.
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("SOURCE_DUCKDB", ROOT / "data/warehouse/nyc_rides.duckdb"))
TARGET = Path(os.environ.get("TARGET_DUCKDB", ROOT / "data/warehouse/deployed.duckdb"))

# Tables used by backend registries, analytics, journey services, and RAG SQL.
# Deliberately excludes raw_trips, raw_zones, staging, and intermediate tables.
TABLES = (
    "canonical_areas",
    "cities",
    "countries",
    "fixed_holidays_extended",
    "gtfs_feeds",
    "model_registry",
    "taxi_zone_lookup",
    "vehicle_profiles",
    "weather_hourly",
    "zone_centroids",
    "zone_fare_stats",
    "zone_hourly_demand",
    "zone_pair_flows",
)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source DuckDB file not found: {SOURCE}")
    if TARGET.exists():
        raise FileExistsError(f"Refusing to overwrite existing target: {TARGET}")

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    source = duckdb.connect(str(SOURCE), read_only=True)
    target = duckdb.connect(str(TARGET))
    try:
        available = {row[0] for row in source.execute("SHOW TABLES").fetchall()}
        missing = sorted(set(TABLES) - available)
        if missing:
            raise RuntimeError(f"Source is missing required tables: {', '.join(missing)}")
        target.execute("ATTACH ? AS source (READ_ONLY)", [str(SOURCE)])
        for table in TABLES:
            target.execute(f'CREATE TABLE "{table}" AS SELECT * FROM source."{table}"')
        target.execute("DETACH source")
    finally:
        target.close()
        source.close()

    print(f"Created {TARGET} ({TARGET.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
