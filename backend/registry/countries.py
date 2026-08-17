"""Country registry (SPEC-013 FR-4) -- thin query module over the seeded
`countries` dbt table plus the `cities`/`global_cities` tables, loaded once
at startup (rule 8: ~250-row-max dimension table, trivially small).

`supported`/`supported_city_count` are never stored -- derived at query time
from a UNION of `cities` (the 2-row registered-city table) and
`global_cities` (SPEC-016's 519-row WorldMove-backed registry): a country is
"supported" iff it has >=1 row in either. Before this fix it only counted
`cities`, so every country except nyc/london's own (US/GB) reported
`supported: false` regardless of real global_cities coverage (found
2026-08-16) -- matches the Data Design tradeoff in specs/013 (avoids a
denormalized flag that can drift from either city list).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

_countries: dict[str, dict] = {}       # iso_code -> {iso_code, name}
_city_counts: dict[str, int] = {}      # iso_code -> number of cities


def load() -> None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        country_rows = con.execute("select iso_code, name from countries").fetchall()
        count_rows = con.execute(
            """
            select country_code, count(distinct city_id) from (
                select id as city_id, country_code from cities
                union
                select city_id, country_code from global_cities
            )
            group by 1
            """
        ).fetchall()
    finally:
        con.close()

    _countries.clear()
    _countries.update({iso_code: {"iso_code": iso_code, "name": name} for iso_code, name in country_rows})
    _city_counts.clear()
    _city_counts.update({code: int(n) for code, n in count_rows})


def _with_support(country: dict) -> dict:
    count = _city_counts.get(country["iso_code"], 0)
    return {**country, "supported": count > 0, "supported_city_count": count}


def list_countries() -> list[dict]:
    return [_with_support(c) for c in _countries.values()]


def get_country(iso_code: str) -> dict | None:
    country = _countries.get(iso_code.upper())
    return _with_support(country) if country else None
