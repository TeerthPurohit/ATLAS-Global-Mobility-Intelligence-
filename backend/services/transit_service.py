"""Real transit-stop-density signal from ingested GTFS static feeds
(scripts/ingest_gtfs_feeds.py) -- reads the small per-city gtfs_stops
dimension table, never the request-time-fetches-a-zip pattern (rule 8: bulk
reference data is ingested once, not re-downloaded per request).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.services import model_service  # noqa: E402

_CITY_WAREHOUSES = {
    "nyc": REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb",
    "london": REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb",
}


def count_stops_near(city_id: str, lat: float, lon: float, radius_km: float = 5.0) -> int | None:
    warehouse = _CITY_WAREHOUSES.get(city_id)
    if warehouse is None or not warehouse.exists():
        return None
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        tables = {r[0] for r in con.execute("show tables").fetchall()}
        if "gtfs_stops" not in tables:
            return None
        # Small dimension table (hundreds-thousands of rows for a city) --
        # a Python-side haversine filter here is fine under rule 8, this
        # isn't a raw-trips scan.
        rows = con.execute("SELECT lat, lon FROM gtfs_stops WHERE city_id = ?", [city_id]).fetchall()
    finally:
        con.close()
    if not rows:
        return None
    return sum(
        1 for stop_lat, stop_lon in rows
        if model_service.haversine_miles((lat, lon), (stop_lat, stop_lon)) * 1.60934 <= radius_km
    )
