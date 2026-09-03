"""Create the read-only DuckDB artifact used by the deployed API.

The local warehouse contains raw and intermediate trip tables that are not
needed by the serving application. Keep this export deterministic and never
overwrite the source warehouse.

Beyond copying the serving tables, this precomputes the handful of facts the
API derives from the *excluded* tables and stores them in a `serving_metadata`
table (ADR-005: the deployed backend loads only precomputed artifacts, and no
raw-table scan happens on any request path):

- row counts and column schemas for stg_trips/stg_zones/int_trips_enriched,
  which back /warehouse/stats and /warehouse/tables. Without these the deployed
  API 500s, because stg_trips/stg_zones are dbt views over data/raw/*.parquet
  and raw TLC data is never shipped.
- the citywide baseline avg_speed_mph journey_service needs at startup, instead
  of re-scanning 113M rows every time a process boots.

Every value here is measured from the real warehouse at build time -- what
changes is *when* it is computed, not whether it was actually observed. A fact
that cannot be computed is stored as null, never guessed (rule 2).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
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

# Excluded from the artifact but still reported by /warehouse/stats and
# /warehouse/tables -- see backend/services/platform_service.py WAREHOUSE_TABLES.
DESCRIBED_ONLY_TABLES = ("stg_trips", "stg_zones", "int_trips_enriched")


def _describe(con: duckdb.DuckDBPyConnection, table: str) -> list[dict]:
    """DESCRIBE as plain Python dicts, matching the shape platform_service
    serves from a live `describe` (column_name/column_type/null/key/...)."""
    result = con.execute(f'describe "{table}"')
    columns = [d[0] for d in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _collect_metadata(source: duckdb.DuckDBPyConnection) -> dict[str, object]:
    """Measure the facts the deployed API can no longer compute for itself."""
    row_counts: dict[str, int | None] = {}
    table_columns: dict[str, list[dict] | None] = {}

    for table in DESCRIBED_ONLY_TABLES:
        started = time.time()
        try:
            row_counts[table] = source.execute(f'select count(*) from "{table}"').fetchone()[0]
            table_columns[table] = _describe(source, table)
            print(f"  {table}: {row_counts[table]:,} rows ({time.time() - started:.1f}s)")
        except Exception as exc:  # noqa: BLE001
            # A view whose underlying parquet is missing, most likely. Record
            # the gap honestly rather than inventing a count.
            row_counts[table] = None
            table_columns[table] = None
            print(f"  {table}: UNAVAILABLE -- {exc}")

    started = time.time()
    try:
        baseline = source.execute(
            "SELECT avg(avg_speed_mph) FROM int_trips_enriched WHERE avg_speed_mph IS NOT NULL"
        ).fetchone()[0]
        baseline = float(baseline) if baseline is not None else None
        print(f"  baseline_avg_speed_mph: {baseline} ({time.time() - started:.1f}s)")
    except Exception as exc:  # noqa: BLE001
        baseline = None
        print(f"  baseline_avg_speed_mph: UNAVAILABLE -- {exc}")

    stat = SOURCE.stat()
    return {
        "row_counts": row_counts,
        "table_columns": table_columns,
        "baseline_avg_speed_mph": baseline,
        # Provenance so a stale artifact is identifiable. Size+mtime rather
        # than a content hash: hashing a 12GB file on every build costs more
        # than the ambiguity it removes for a single-writer pipeline.
        "provenance": {
            "source": str(SOURCE),
            "source_bytes": stat.st_size,
            "source_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "built_at": datetime.now(timezone.utc).isoformat(),
        },
    }


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

        # ATTACH takes no bound parameters in DuckDB -- inline the path,
        # escaping quotes rather than binding it.
        target.execute(f"ATTACH '{str(SOURCE).replace(chr(39), chr(39) * 2)}' AS source (READ_ONLY)")
        for table in TABLES:
            target.execute(f'CREATE TABLE "{table}" AS SELECT * FROM source."{table}"')
        target.execute("DETACH source")

        print("Measuring facts for the excluded tables:")
        metadata = _collect_metadata(source)
        target.execute("CREATE TABLE serving_metadata (key VARCHAR, value VARCHAR)")
        target.executemany(
            "INSERT INTO serving_metadata VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in metadata.items()],
        )
    finally:
        target.close()
        source.close()

    print(f"Created {TARGET} ({TARGET.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
