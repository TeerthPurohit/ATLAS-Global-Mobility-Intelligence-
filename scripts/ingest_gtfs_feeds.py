"""Download, unzip, and load GTFS static feeds' stops.txt into each city's
own warehouse (bulk reference data, ingested once like scripts/
ingest_tfl_cycle_hire.py -- not a request-time adapter, since GTFS static
feeds are large and update infrequently).

`feed_url` in dbt_project/seeds/gtfs_feeds.csv is a placeholder
(VERIFY_BEFORE_USE) -- before running this script for real, look up each
agency's current GTFS static feed URL from their official developer/open-data
page (e.g. MTA's at https://new.mta.info/developers, TfL's at
https://api.tfl.gov.uk/) and replace the placeholder, updating last_verified
to today's date. This mirrors ingest_tfl_cycle_hire.py's rule-5 discipline:
record exactly what URL was pulled and when, never a guessed pattern. This
script refuses to run against the placeholder rather than silently no-oping
or (worse) requesting a guessed URL.
"""
from __future__ import annotations

import csv
import sys
import urllib.request
import zipfile
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
SEED_PATH = REPO_ROOT / "dbt_project" / "seeds" / "gtfs_feeds.csv"
RAW_DIR = REPO_ROOT / "data" / "raw" / "gtfs"

_CITY_WAREHOUSES = {
    "nyc": REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb",
    "london": REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb",
}


def _read_feeds() -> list[dict]:
    with open(SEED_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _download(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (data-pipeline; +nyc-ride-intelligence)"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    print(f"  -> {dest.name} ({dest.stat().st_size:,} bytes)")


def _fetch_and_extract_stops(feed_url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "gtfs_feed.zip"
    _download(feed_url, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract("stops.txt", dest_dir)
    return dest_dir / "stops.txt"


def load_stops(city_id: str, stops_txt: Path, warehouse_path: Path) -> int:
    con = duckdb.connect(str(warehouse_path))
    try:
        con.execute(
            "CREATE OR REPLACE TABLE gtfs_stops AS "
            "SELECT ? AS city_id, stop_id, stop_name, CAST(stop_lat AS DOUBLE) AS lat, CAST(stop_lon AS DOUBLE) AS lon "
            "FROM read_csv(?, header=true)",
            [city_id, str(stops_txt)],
        )
        return con.execute("SELECT COUNT(*) FROM gtfs_stops WHERE city_id = ?", [city_id]).fetchone()[0]
    finally:
        con.close()


def main() -> None:
    feeds = _read_feeds()
    for feed in feeds:
        city_id = feed["city_id"]
        if feed["feed_url"] == "VERIFY_BEFORE_USE":
            print(f"Skipping {city_id}: feed_url is still the unverified placeholder. "
                  f"See this script's module docstring for how to fill it in.")
            continue
        warehouse = _CITY_WAREHOUSES.get(city_id)
        if warehouse is None:
            print(f"Skipping {city_id}: no known warehouse path registered in this script.")
            continue
        print(f"Ingesting GTFS feed for {city_id} ({feed['agency_name']})...")
        stops_txt = _fetch_and_extract_stops(feed["feed_url"], RAW_DIR / city_id)
        n = load_stops(city_id, stops_txt, warehouse)
        print(f"  loaded {n:,} stops into {warehouse.name}'s gtfs_stops table")


if __name__ == "__main__":
    main()
