"""Registry for global_cities (docs/superpowers/plans/2026-08-09-global-city-registry.md)
-- the stable city_id -> tier/population lookup backing global_geography_service's
model_status and confidence fields. Same load-once-at-startup pattern as
backend/registry/cities.py (rule 8: no query-time table scans)."""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

_COLUMNS = (
    "city_id", "name", "country_code", "latitude", "longitude", "timezone",
    "currency", "population", "population_source", "model_status", "worldmove_available",
)

_cities: dict[str, dict] = {}
_by_name: dict[tuple[str, str], dict] = {}


def load() -> None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        rows = con.execute(f"SELECT {', '.join(_COLUMNS)} FROM global_cities").fetchall()
    finally:
        con.close()
    _cities.clear()
    _by_name.clear()
    for row in rows:
        city = dict(zip(_COLUMNS, row))
        _cities[city["city_id"]] = city
        if city["name"] and city["country_code"]:
            _by_name[(city["country_code"].upper(), city["name"].lower())] = city


def get_city(city_id: str) -> dict | None:
    if not _cities:
        load()  # defensive lazy-load, same rationale as backend/registry/cities.py
    return _cities.get(city_id)


def find_by_name(city_name: str, country_code: str) -> dict | None:
    if not _cities:
        load()
    if not city_name or not country_code:
        return None
    return _by_name.get((country_code.upper(), city_name.lower()))


def list_cities(model_status: str | None = None) -> list[dict]:
    if not _cities:
        load()
    rows = _cities.values()
    if model_status:
        rows = [c for c in rows if c["model_status"] == model_status]
    return list(rows)
