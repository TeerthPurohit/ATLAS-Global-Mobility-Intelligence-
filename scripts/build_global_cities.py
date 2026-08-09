"""Build global_cities: the stable, honest registry of every city this
platform can talk about, uniting the 2 real registered cities (cities.csv
-- OBSERVED, they have trained models) with the 522 WorldMove cities
(worldmove_city_population -- TRANSFER, population/mobility prior only,
no trip-level data). See docs/superpowers/plans/2026-08-09-global-city-registry.md.

Existing city_ids ("nyc", "london") are preserved exactly; WorldMove rows
get a new stable {COUNTRY_CODE}_{CITY_NAME} key since they have no prior key
to preserve (checked for collisions -- none exist as of the 522-city load).
"""
import os
import re
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"))


def _slug(country_code: str, city_name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "_", city_name.strip()).strip("_").upper()
    return f"{country_code.upper()}_{name}"


def main():
    con = duckdb.connect(DUCKDB_PATH)

    con.execute("""
        CREATE OR REPLACE TABLE global_cities (
            city_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            country_code VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            timezone VARCHAR,
            currency VARCHAR,
            population DOUBLE,
            population_source VARCHAR,
            model_status VARCHAR,
            worldmove_available BOOLEAN
        )
    """)

    registered = con.execute(
        "SELECT id, name, country_code, latitude, longitude, timezone, currency, population FROM cities"
    ).fetchall()
    rows = [
        (city_id, name, country_code, lat, lon, tz, currency, float(population) if population else None,
         "registered", "OBSERVED", False)
        for city_id, name, country_code, lat, lon, tz, currency, population in registered
    ]

    worldmove = con.execute(
        "SELECT country_code, city_name, population_total FROM worldmove_city_population"
    ).fetchall()
    seen_ids = {r[0] for r in rows}
    for country_code, city_name, population_total in worldmove:
        city_id = _slug(country_code, city_name)
        if city_id in seen_ids:
            raise ValueError(f"city_id collision: {city_id} ({city_name}, {country_code})")
        seen_ids.add(city_id)
        rows.append((
            city_id, city_name, country_code, None, None, None, None,
            population_total, "worldmove_estimate", "TRANSFER", True,
        ))

    con.executemany(
        "INSERT INTO global_cities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    n = con.execute("SELECT count(*) FROM global_cities").fetchone()[0]
    print(f"global_cities: {n:,} rows loaded")
    con.close()


if __name__ == "__main__":
    main()
