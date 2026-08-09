"""Unit tests for scripts/build_global_cities.py's two correctness rules:
a registered city without an active model_registry row must not get a free
OBSERVED tier, and a WorldMove row must not duplicate an already-registered
city under a second city_id."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _build(tmp_path, cities_rows, worldmove_rows, model_registry_rows):
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE cities (id VARCHAR, name VARCHAR, country_code VARCHAR, "
        "latitude DOUBLE, longitude DOUBLE, timezone VARCHAR, currency VARCHAR, population INTEGER)"
    )
    con.executemany("INSERT INTO cities VALUES (?, ?, ?, ?, ?, ?, ?, ?)", cities_rows)
    con.execute(
        "CREATE TABLE worldmove_city_population (country_code VARCHAR, city_name VARCHAR, population_total DOUBLE)"
    )
    if worldmove_rows:
        con.executemany("INSERT INTO worldmove_city_population VALUES (?, ?, ?)", worldmove_rows)
    con.execute("CREATE TABLE model_registry (city_id VARCHAR, status VARCHAR)")
    con.executemany("INSERT INTO model_registry VALUES (?, ?)", model_registry_rows)
    con.close()

    os.environ["DUCKDB_PATH"] = str(db_path)
    import scripts.build_global_cities as build_global_cities
    importlib.reload(build_global_cities)
    build_global_cities.main()
    del os.environ["DUCKDB_PATH"]

    con = duckdb.connect(str(db_path), read_only=True)
    rows = con.execute("SELECT city_id, name, country_code, model_status FROM global_cities").fetchall()
    con.close()
    return rows


def test_registered_city_without_active_model_is_transfer(tmp_path):
    rows = _build(
        tmp_path,
        cities_rows=[("paris", "Paris", "FR", 48.85, 2.35, "Europe/Paris", "EUR", 2148000)],
        worldmove_rows=[],
        model_registry_rows=[("paris", "inactive")],
    )
    assert dict((r[0], r[3]) for r in rows) == {"paris": "TRANSFER"}


def test_worldmove_row_colliding_with_registered_city_is_skipped(tmp_path):
    rows = _build(
        tmp_path,
        cities_rows=[("london", "London", "GB", 51.5, -0.12, "Europe/London", "GBP", 9000000)],
        worldmove_rows=[("GB", "London", 9000000.0), ("GB", "Manchester", 550000.0)],
        model_registry_rows=[("london", "active")],
    )
    by_name = {(r[2], r[1].lower()): r[0] for r in rows}
    assert by_name[("GB", "london")] == "london"  # not overwritten by a second WorldMove row
    assert ("GB", "manchester") in by_name  # non-colliding WorldMove rows still load
    assert len(rows) == 2
