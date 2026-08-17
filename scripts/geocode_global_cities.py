"""
scripts/geocode_global_cities.py
Geocoding backfill using GeoNames free API.
Progress tracked via DB — safe to stop/restart anytime.

Run from repo root (with backend stopped):
  docker compose stop backend
  .venv\\Scripts\\python.exe scripts\\geocode_global_cities.py
  docker compose start backend
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import duckdb
import httpx
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

WAREHOUSE = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
GEONAMES_USER = os.getenv("GEONAMES_USERNAME", "")

DELAY_S = 0.12       # 120ms between requests
BATCH_COMMIT = 20

if not GEONAMES_USER:
    sys.exit("ERROR: GEONAMES_USERNAME not set in .env")

print(f"Warehouse  : {WAREHOUSE}")
print(f"GeoNames   : {GEONAMES_USER}")

# ── Static country → ISO 4217 currency ───────────────────────────────────────
CURRENCY: dict[str, str] = {
    "AE": "AED", "AT": "EUR", "AU": "AUD", "BE": "EUR", "BH": "BHD",
    "CA": "CAD", "CH": "CHF", "CZ": "CZK", "DE": "EUR", "DK": "DKK",
    "EE": "EUR", "ES": "EUR", "FI": "EUR", "FR": "EUR", "GB": "GBP",
    "GR": "EUR", "HK": "HKD", "HR": "EUR", "HU": "HUF", "IE": "EUR",
    "IL": "ILS", "IN": "INR", "IS": "ISK", "IT": "EUR", "JP": "JPY",
    "KR": "KRW", "LI": "CHF", "LT": "EUR", "LU": "EUR", "MC": "EUR",
    "MT": "EUR", "NL": "EUR", "NO": "NOK", "NZ": "NZD", "OM": "OMR",
    "PL": "PLN", "PT": "EUR", "QA": "QAR", "SA": "SAR", "SE": "SEK",
    "SG": "SGD", "SI": "EUR", "SK": "EUR", "TW": "TWD", "US": "USD",
}

GEOCODE_URL = "http://api.geonames.org/searchJSON"
TZ_URL      = "http://api.geonames.org/timezoneJSON"


def geocode(name: str, cc: str, client: httpx.Client) -> tuple[float, float] | None:
    for attempt, params in enumerate([
        {"name": name, "country": cc, "featureClass": "P",
         "orderby": "population", "maxRows": 1,
         "username": GEONAMES_USER, "type": "json"},
        {"name_equals": name, "country": cc, "maxRows": 1,
         "username": GEONAMES_USER, "type": "json"},
    ]):
        try:
            if attempt > 0:
                time.sleep(DELAY_S)
            r = client.get(GEOCODE_URL, params=params, timeout=20)
            hits = r.json().get("geonames", [])
            if hits:
                return float(hits[0]["lat"]), float(hits[0]["lng"])
        except Exception as e:
            print(f"    geocode error ({name},{cc}): {e}")
            time.sleep(1.0)
    return None


def get_tz(lat: float, lng: float, client: httpx.Client) -> str | None:
    try:
        r = client.get(TZ_URL, params={
            "lat": lat, "lng": lng, "username": GEONAMES_USER,
        }, timeout=20)
        return r.json().get("timezoneId")
    except Exception as e:
        print(f"    tz error ({lat},{lng}): {e}")
        time.sleep(1.0)
        return None


def flush(con: duckdb.DuckDBPyConnection, updates: list[tuple]) -> None:
    if not updates:
        return
    con.executemany(
        "UPDATE global_cities SET latitude=?, longitude=?, timezone=?, currency=? WHERE city_id=?",
        updates,
    )
    print(f"  -> Committed {len(updates)} rows")


def main() -> None:
    if not WAREHOUSE.exists():
        sys.exit(f"Warehouse not found: {WAREHOUSE}")

    con = duckdb.connect(str(WAREHOUSE))

    with httpx.Client() as client:
        # Sanity check
        r = client.get(GEOCODE_URL, params={
            "name": "London", "country": "GB", "maxRows": 1,
            "featureClass": "P", "username": GEONAMES_USER, "type": "json",
        }, timeout=15)
        hits = r.json().get("geonames", [])
        if not hits:
            con.close()
            sys.exit(f"GeoNames test failed: {r.json()}")
        print(f"GeoNames OK — London: {hits[0]['lat']},{hits[0]['lng']}\n")

        # Progress = cities still NULL in DB (restart-safe)
        rows = con.execute(
            "SELECT city_id, name, country_code FROM global_cities "
            "WHERE latitude IS NULL OR longitude IS NULL "
            "ORDER BY country_code, name"
        ).fetchall()

        total_db = con.execute("SELECT COUNT(*) FROM global_cities").fetchone()[0]
        already_done = total_db - len(rows)
        print(f"Total cities     : {total_db}")
        print(f"Already geocoded : {already_done}")
        print(f"Still pending    : {len(rows)}\n")

        if not rows:
            print("All cities already geocoded!")
            _fix_population(con)
            con.close()
            return

        updates: list[tuple] = []
        failed: list[str] = []

        for i, (city_id, name, cc) in enumerate(rows, 1):
            cc = cc or "US"

            result = geocode(name, cc, client)
            time.sleep(DELAY_S)

            if result is None:
                print(f"  [{i:>3}/{len(rows)}] NOT FOUND  {city_id} ({name}, {cc})")
                failed.append(city_id)
                continue

            lat, lng = result
            tz = get_tz(lat, lng, client)
            time.sleep(DELAY_S)
            cur = CURRENCY.get(cc, "USD")

            print(f"  [{i:>3}/{len(rows)}] OK  {city_id:<32} {lat:.4f},{lng:.4f}  {tz}  {cur}")
            updates.append((lat, lng, tz, cur, city_id))

            if len(updates) >= BATCH_COMMIT:
                flush(con, updates)
                updates.clear()

    flush(con, updates)
    _fix_population(con)
    _drop_unresolvable(con)
    con.close()

    ok = len(rows) - len(failed)
    print(f"\n{'='*55}")
    print(f"  Geocoded this run  : {ok}")
    print(f"  Not found          : {len(failed)}")
    if failed:
        print(f"  Failed: {failed}")
    print(f"{'='*55}")
    print("\nNext: docker compose start backend")


def _fix_population(con: duckdb.DuckDBPyConnection) -> None:
    print("\nRounding population to int...")
    con.execute(
        "UPDATE global_cities SET population = CAST(ROUND(population) AS BIGINT) "
        "WHERE population IS NOT NULL"
    )
    print("Population fixed.")


def _drop_unresolvable(con: duckdb.DuckDBPyConnection) -> None:
    """A row still NULL here means every geocode() attempt exhausted (e.g.
    WorldMove's own source tagged the wrong country_code -- Drammen/Norway
    and Suez/Egypt both shipped as country_code='US' in the raw .npy
    metadata, so GeoNames found nothing under that country filter). Kept
    around it's dead weight: no coordinates means unusable for routing/
    distance, and it still pollutes that (wrong) country's search results.
    Only reached after a full, uninterrupted pass -- see main()."""
    dropped = con.execute(
        "SELECT city_id FROM global_cities WHERE latitude IS NULL OR longitude IS NULL"
    ).fetchall()
    if not dropped:
        return
    con.execute("DELETE FROM global_cities WHERE latitude IS NULL OR longitude IS NULL")
    print(f"Dropped {len(dropped)} unresolvable row(s): {[r[0] for r in dropped]}")


if __name__ == "__main__":
    main()
