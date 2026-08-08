"""Correctness tests for the London (Santander Cycle Hire) dbt pipeline
(SPEC-015 FR-1/FR-2). Mirrors tests/test_journey.py's style: real DuckDB
warehouse, skipped if not built, no mocking of the pipeline itself.
"""
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPO_ROOT / "dbt_project"
NYC_DB = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
LONDON_DB = REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb"
DBT_BIN = str(Path(sys.executable).parent / "dbt")  # .venv/Scripts/dbt(.exe)

pytestmark = pytest.mark.skipif(not LONDON_DB.exists(), reason="London warehouse not built")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(LONDON_DB), read_only=True)
    yield c
    c.close()


def test_dbt_test_passes_for_london_models():
    """The actual dbt test suite for the four London models -- pass or warn,
    never a hard failure (dbt exits 0 for warn, 1 for error/fail)."""
    result = subprocess.run(
        [
            DBT_BIN, "test",
            "--project-dir", str(DBT_PROJECT_DIR),
            "--profiles-dir", str(DBT_PROJECT_DIR),
            "--select",
            "stg_london_cycle_journeys", "stg_london_stations",
            "int_london_journeys_enriched", "london_station_hourly_demand",
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]


def test_raw_journeys_loaded(con):
    n = con.execute("SELECT COUNT(*) FROM raw_journeys").fetchone()[0]
    assert n > 0


def test_staging_casts_no_business_logic(con):
    # Staging only drops malformed-length station ids (rule 6) -- shouldn't
    # lose more than a small fraction of rows vs. the raw extract.
    raw_n = con.execute("SELECT COUNT(*) FROM raw_journeys").fetchone()[0]
    stg_n = con.execute("SELECT COUNT(*) FROM stg_london_cycle_journeys").fetchone()[0]
    assert 0 < raw_n - stg_n < raw_n * 0.01


def test_intermediate_applies_duration_outlier_filter(con):
    row = con.execute(
        "SELECT MIN(duration_minutes), MAX(duration_minutes) FROM int_london_journeys_enriched"
    ).fetchone()
    assert row[0] > 0
    assert row[1] <= 1440


def test_mart_shape_mirrors_zone_hourly_demand(con):
    """station_id, trip_date, hour, day_of_week, total_trips,
    avg_duration_min -- real calendar-date grain, same shape discipline as
    zone_hourly_demand's pickup_date/pickup_hour/pickup_location_id (rule 3:
    a real date column is required for the chronological split)."""
    cols = {r[0] for r in con.execute("DESCRIBE london_station_hourly_demand").fetchall()}
    assert {"station_id", "trip_date", "hour", "day_of_week", "total_trips", "avg_duration_min"} <= cols

    row = con.execute(
        "SELECT MIN(hour), MAX(hour), MIN(day_of_week), MAX(day_of_week), MIN(total_trips), "
        "COUNT(DISTINCT trip_date) FROM london_station_hourly_demand"
    ).fetchone()
    assert row[0] >= 0 and row[1] <= 23
    assert row[2] >= 0 and row[3] <= 6
    assert row[4] > 0
    assert row[5] > 30  # real distinct calendar dates, not collapsed to day-of-week


def test_nyc_warehouse_has_no_london_objects():
    """rule 6 / spec-015 ground rule: London is additive-only, NYC's
    warehouse file must not gain any London tables."""
    con_nyc = duckdb.connect(str(NYC_DB), read_only=True)
    try:
        tables = [r[0] for r in con_nyc.execute("SHOW TABLES").fetchall()]
    finally:
        con_nyc.close()
    assert not [t for t in tables if "london" in t.lower()]


if __name__ == "__main__":
    # ponytail: smallest runnable self-check, not a full pytest invocation.
    if not LONDON_DB.exists():
        print("London warehouse not built, skipping self-check")
    else:
        c = duckdb.connect(str(LONDON_DB), read_only=True)
        test_raw_journeys_loaded(c)
        test_staging_casts_no_business_logic(c)
        test_intermediate_applies_duration_outlier_filter(c)
        test_mart_shape_mirrors_zone_hourly_demand(c)
        c.close()
        test_nyc_warehouse_has_no_london_objects()
        print("London pipeline self-check OK")
