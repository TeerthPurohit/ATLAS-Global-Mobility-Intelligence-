"""GTFS transit feed registry -- exact mirror of backend/registry/models.py's
shape. Real feeds only: a city with no row here honestly has no transit
coverage, never a fabricated one.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

_feeds: dict[str, dict] = {}


def load() -> None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        rows = con.execute("select city_id, agency_name, feed_url, format, last_verified from gtfs_feeds").fetchall()
    finally:
        con.close()
    _feeds.clear()
    for city_id, agency_name, feed_url, format_, last_verified in rows:
        _feeds[city_id] = {"agency_name": agency_name, "feed_url": feed_url, "format": format_, "last_verified": last_verified}


_CITY_WAREHOUSES = {
    "nyc": WAREHOUSE_PATH,
    "london": REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb",
}


def get_feed(city_id: str) -> dict | None:
    if not _feeds:
        load()  # defensive lazy-load -- see backend/registry/cities.py's get_city() for why
    return _feeds.get(city_id)


def has_feed(city_id: str) -> bool:
    """True only once a real feed is both configured (not the unverified
    placeholder) AND actually ingested (gtfs_stops has real rows) -- a
    registered-but-never-ingested feed_url is not coverage yet."""
    feed = get_feed(city_id)
    if feed is None or feed["feed_url"] == "VERIFY_BEFORE_USE":
        return False
    warehouse = _CITY_WAREHOUSES.get(city_id)
    if warehouse is None or not warehouse.exists():
        return False
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        tables = {r[0] for r in con.execute("show tables").fetchall()}
        if "gtfs_stops" not in tables:
            return False
        count = con.execute("select count(*) from gtfs_stops where city_id = ?", [city_id]).fetchone()[0]
        return count > 0
    finally:
        con.close()
