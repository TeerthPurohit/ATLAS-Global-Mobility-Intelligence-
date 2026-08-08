"""Download and load TfL Santander Cycle Hire journey data into DuckDB.

Mirrors scripts/load_raw_to_duckdb.py's pattern for NYC (raw table in,
verified by row count), but this script also performs the download step
since TfL's journey CSVs aren't vendored in the repo the way NYC's parquet
sample is.

Sources (both public, no auth/key required):
- Journeys: https://cycling.data.tfl.gov.uk/usage-stats/ (public S3-style
  bucket listing at https://s3-eu-west-1.amazonaws.com/cycling.data.tfl.gov.uk/).
- Station locations: https://api.tfl.gov.uk/BikePoint (TfL Unified API).
  The bulk journey CSVs have no lat/lon column at all -- BikePoint's
  `TerminalName` field is the join key back to the journeys' station number
  columns (both are the same zero-padded docking-station terminal id, e.g.
  "001211").

Scope (rule 5 -- record exactly what was pulled, since "since 2015" and
"three recent months" are very different datasets): the bucket listing goes
back to Sept 2015 and forward to ~today; this script pulls six biweekly
extracts covering Jan, Mar, and May 2026 -- three real months on the same
skip-a-month cadence as NYC's Jan/Mar/Jun 2024 scope (see
.claude/memory.md), not the full multi-year archive. JOURNEY_FILES below are
the literal current keys from that bucket listing (checked 2026-08-08), not
a guessed naming pattern -- TfL's file-numbering/naming has changed over the
years (see readme.txt in the bucket), so this is deliberately not a glob.
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "london"
LOOKUP_DIR = REPO_ROOT / "data" / "lookup"
SEED_DIR = REPO_ROOT / "dbt_project" / "seeds"
DB_PATH = Path(os.environ.get("LONDON_DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb")))

TFL_BASE = "https://cycling.data.tfl.gov.uk/usage-stats/"
BIKEPOINT_URL = "https://api.tfl.gov.uk/BikePoint"

JOURNEY_FILES = [
    "435JourneyDataExtract01Jan2026-15Jan2026.csv",
    "436JourneyDataExtract16Jan2026-31Jan2026.csv",
    "439JourneyDataExtract01Mar2026-15Mar2026.csv",
    "440JourneyDataExtract15Mar2026-31Mar2026.csv",
    "443JourneyDataExtract01May2026-16May2026.csv",
    "444JourneyDataExtract17May2026-31May2026.csv",
]

# Explicit types instead of read_csv_auto's per-file sniffer: guarantees the
# same schema (esp. station numbers staying zero-padded VARCHAR, not
# silently drifting to INTEGER on a file where the sniffer guesses
# differently) across a multi-file union.
CSV_COLUMNS = {
    "Number": "BIGINT",
    "Start date": "TIMESTAMP",
    "Start station number": "VARCHAR",
    "Start station": "VARCHAR",
    "End date": "TIMESTAMP",
    "End station number": "VARCHAR",
    "End station": "VARCHAR",
    "Bike number": "BIGINT",
    "Bike model": "VARCHAR",
    "Total duration": "VARCHAR",
    "Total duration (ms)": "BIGINT",
}


def _download(url: str, dest: Path, min_bytes: int = 1000) -> None:
    if dest.exists() and dest.stat().st_size > min_bytes:
        print(f"  already have {dest.name} ({dest.stat().st_size:,} bytes)")
        return
    print(f"  downloading {url}")
    # cycling.data.tfl.gov.uk's CloudFront front-end 403s urllib's default
    # User-Agent; a browser-like UA is enough to get past it.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (data-pipeline; +nyc-ride-intelligence)"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    print(f"  -> {dest.name} ({dest.stat().st_size:,} bytes)")


def fetch_journeys() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in JOURNEY_FILES:
        _download(TFL_BASE + name, RAW_DIR / name)


def fetch_stations() -> int:
    """Pull live BikePoint locations and write the same station_id/name/lat/lon
    shape to two places: the dbt seed (for staging joins) and data/lookup/
    (for algorithms/spatial's KD-tree, matching zone_centroids.csv's shape)."""
    LOOKUP_DIR.mkdir(parents=True, exist_ok=True)
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / "bikepoint_raw.json"
    _download(BIKEPOINT_URL, dest, min_bytes=10_000)

    with open(dest, encoding="utf-8") as f:
        points = json.load(f)

    rows = []
    for p in points:
        terminal = next(
            (a["value"] for a in p.get("additionalProperties", []) if a["key"] == "TerminalName"),
            None,
        )
        if not terminal or p.get("lat") is None or p.get("lon") is None:
            continue
        rows.append((terminal, p["commonName"], p["lat"], p["lon"]))

    for path in (LOOKUP_DIR / "london_station_centroids.csv", SEED_DIR / "london_stations.csv"):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["station_id", "name", "latitude", "longitude"])
            w.writerows(rows)

    print(f"  wrote {len(rows)} stations (of {len(points)} BikePoints) to lookup + seed CSVs")
    return len(rows)


def load_duckdb() -> tuple[int, tuple]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    file_list = [str(RAW_DIR / name) for name in JOURNEY_FILES]
    con.execute(
        "CREATE OR REPLACE TABLE raw_journeys AS "
        "SELECT * FROM read_csv(?, header=true, columns=?)",
        [file_list, CSV_COLUMNS],
    )
    row_count = con.execute("SELECT COUNT(*) FROM raw_journeys").fetchone()[0]
    date_range = con.execute('SELECT MIN("Start date"), MAX("Start date") FROM raw_journeys').fetchone()
    con.close()
    return row_count, date_range


def main() -> None:
    print("Fetching TfL Santander Cycle Hire journey extracts...")
    fetch_journeys()

    print("Fetching TfL BikePoint station locations...")
    n_stations = fetch_stations()

    print("Loading journeys into DuckDB...")
    row_count, date_range = load_duckdb()

    manifest = {
        "source_files": JOURNEY_FILES,
        "source_url_base": TFL_BASE,
        "bikepoint_url": BIKEPOINT_URL,
        "pulled_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "row_count": row_count,
        "min_start_date": str(date_range[0]),
        "max_start_date": str(date_range[1]),
        "n_stations": n_stations,
        "duckdb_path": str(DB_PATH),
    }
    with open(RAW_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"raw_journeys: {row_count:,} rows, {date_range[0]} -> {date_range[1]}")
    print(f"stations: {n_stations:,}")
    print(f"manifest written to {RAW_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
