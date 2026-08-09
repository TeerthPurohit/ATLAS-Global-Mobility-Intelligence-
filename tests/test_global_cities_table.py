from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DB_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"


def _table_exists(con) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'global_cities'"
    ).fetchone()[0] > 0


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


def test_global_cities_table_exists_and_populated(con):
    assert _table_exists(con), "run scripts/build_global_cities.py first"
    n = con.execute("SELECT count(*) FROM global_cities").fetchone()[0]
    assert n == 524, f"expected 2 registered + 522 WorldMove cities, got {n}"


def test_global_cities_no_duplicate_ids(con):
    dupes = con.execute(
        "SELECT city_id, count(*) c FROM global_cities GROUP BY 1 HAVING count(*) > 1"
    ).fetchall()
    assert dupes == []


def test_registered_cities_are_observed(con):
    rows = con.execute(
        "SELECT city_id, model_status, population_source FROM global_cities WHERE city_id IN ('nyc', 'london')"
    ).fetchall()
    assert len(rows) == 2
    for city_id, model_status, population_source in rows:
        assert model_status == "OBSERVED", city_id
        assert population_source == "registered", city_id


def test_worldmove_cities_are_transfer(con):
    row = con.execute(
        "SELECT model_status, population_source, worldmove_available FROM global_cities WHERE city_id = 'IN_JAIPUR'"
    ).fetchone()
    assert row is not None, "Jaipur should be present from worldmove_city_population"
    model_status, population_source, worldmove_available = row
    assert model_status == "TRANSFER"
    assert population_source == "worldmove_estimate"
    assert worldmove_available is True
