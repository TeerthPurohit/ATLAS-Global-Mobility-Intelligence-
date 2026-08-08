"""Correctness tests for the GTFS transit feed registry. No live network
call here (no verified feed URL to hit in CI) -- seeds a synthetic
gtfs_stops table directly and asserts the registry/context envelope
correctly distinguishes "feed registered but unverified/never ingested"
from "feed actually ingested with real stops."
"""
import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.registry import transit as transit_registry  # noqa: E402
from backend.services import transit_service  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


def test_unverified_placeholder_feed_reports_no_coverage():
    transit_registry.load()
    # Both seeded rows ship with the VERIFY_BEFORE_USE placeholder until a
    # real feed URL is confirmed and scripts/ingest_gtfs_feeds.py is run.
    assert transit_registry.has_feed("nyc") is False
    assert transit_registry.has_feed("mumbai") is False  # never registered at all


def test_count_stops_near_returns_none_without_gtfs_stops_table():
    result = transit_service.count_stops_near("nyc", 40.7580, -73.9855)
    assert result is None


def test_count_stops_near_with_synthetic_stops():
    # Seed a tiny synthetic gtfs_stops table directly (bypassing real
    # ingestion, which needs a verified feed URL) to prove the query/distance
    # logic itself is correct.
    con = duckdb.connect(str(WAREHOUSE_PATH))
    try:
        con.execute(
            "CREATE OR REPLACE TABLE gtfs_stops AS SELECT * FROM (VALUES "
            "('nyc', 's1', 'Times Square', 40.7580, -73.9855), "
            "('nyc', 's2', 'Far Away', 41.5, -75.0)"
            ") AS t(city_id, stop_id, stop_name, lat, lon)"
        )
    finally:
        con.close()
    try:
        count = transit_service.count_stops_near("nyc", 40.7580, -73.9855, radius_km=5.0)
        assert count == 1  # only the nearby stop, not the far-away one
    finally:
        con = duckdb.connect(str(WAREHOUSE_PATH))
        con.execute("DROP TABLE IF EXISTS gtfs_stops")
        con.close()


def demo() -> None:
    transit_registry.load()
    test_unverified_placeholder_feed_reports_no_coverage()
    test_count_stops_near_returns_none_without_gtfs_stops_table()
    test_count_stops_near_with_synthetic_stops()
    print("test_gtfs_registry demo OK")


if __name__ == "__main__":
    demo()
