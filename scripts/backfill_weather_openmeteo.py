"""Backfill real historical hourly weather (temperature + precipitation) for
every date each city's warehouse actually has, via Open-Meteo's free,
keyless historical archive API. Writes dbt_project/seeds/weather_hourly.csv,
loaded as a normal dbt seed and joined into zone_hourly_demand /
london_station_hourly_demand at (date, hour) grain -- city-level, never
per-zone/per-station, since weather doesn't meaningfully vary within one city.

This is what actually lifts ADR-008's "weather can never be a retrainable
historical feature" ceiling (see the dated Update section appended there) --
OpenWeatherMap's free tier has no historical backfill; Open-Meteo's
archive-api.open-meteo.com/v1/era5 does, keylessly, for any date/location.

Deliberately only 2 fields (temperature_c, precipitation_mm), not the wider
wishlist (humidity/wind/etc.) -- add more only if a retrain shows they're
needed (ponytail: don't fetch/store covariates nothing consumes yet).

Real dates queried directly from each warehouse (never a hardcoded/assumed
date list -- rule 5), at each city's registered centroid lat/lon from
dbt_project/seeds/cities.csv.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import duckdb
import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SEED_PATH = REPO_ROOT / "dbt_project" / "seeds" / "weather_hourly.csv"
MANIFEST_PATH = REPO_ROOT / "data" / "raw" / "weather" / "manifest.json"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/era5"

# city_id -> (warehouse path, date column, table, lat, lon) -- lat/lon match
# dbt_project/seeds/cities.csv exactly (not re-derived).
_CITY_WAREHOUSES = {
    "nyc": {
        "path": REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb",
        "table": "zone_hourly_demand",
        "date_col": "pickup_date",
        "lat": 40.7128,
        "lon": -74.0060,
    },
    "london": {
        "path": REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb",
        "table": "london_station_hourly_demand",
        "date_col": "trip_date",
        "lat": 51.5074,
        "lon": -0.1278,
    },
}


def _real_dates_needed(city_id: str) -> list[str]:
    cfg = _CITY_WAREHOUSES[city_id]
    con = duckdb.connect(str(cfg["path"]), read_only=True)
    try:
        rows = con.execute(f"SELECT DISTINCT {cfg['date_col']} FROM {cfg['table']} ORDER BY 1").fetchall()
    finally:
        con.close()
    return [str(r[0]) for r in rows]


def fetch_city_weather(city_id: str) -> tuple[list[dict], list[str]]:
    cfg = _CITY_WAREHOUSES[city_id]
    dates = _real_dates_needed(city_id)
    if not dates:
        print(f"  {city_id}: no real dates found in {cfg['table']}, skipping")
        return [], []

    print(f"  {city_id}: {len(dates)} real dates ({dates[0]}..{dates[-1]}), fetching from Open-Meteo archive...")
    resp = httpx.get(
        ARCHIVE_URL,
        params={
            "latitude": cfg["lat"], "longitude": cfg["lon"],
            "start_date": dates[0], "end_date": dates[-1],
            "hourly": "temperature_2m,precipitation",
            "timezone": "UTC",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    hourly = resp.json()["hourly"]

    wanted_dates = set(dates)
    rows = []
    for ts, temp, precip in zip(hourly["time"], hourly["temperature_2m"], hourly["precipitation"]):
        date_str, hour_str = ts.split("T")
        if date_str in wanted_dates:
            rows.append({
                "city_id": city_id, "date": date_str, "hour": int(hour_str[:2]),
                "temperature_c": temp, "precipitation_mm": precip,
            })
    return rows, dates


def main() -> None:
    all_rows: list[dict] = []
    manifest: dict = {"pulled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cities": {}}

    print("Backfilling historical weather via Open-Meteo archive API...")
    for city_id in _CITY_WAREHOUSES:
        rows, dates = fetch_city_weather(city_id)
        all_rows.extend(rows)
        manifest["cities"][city_id] = {"n_dates": len(dates), "n_hourly_rows": len(rows)}

    if not all_rows:
        print("No rows fetched -- aborting without touching the seed file.")
        return

    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SEED_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["city_id", "date", "hour", "temperature_c", "precipitation_mm"])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows to {SEED_PATH}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
