"""The slim serving artifact must serve the same facts as the full warehouse.

ADR-005 has the deployed backend load only precomputed artifacts -- mart tables,
never raw trips. `scripts/build_deployed_duckdb.py` builds that artifact and
measures, once, the handful of facts the API otherwise derives from the excluded
113M-row tables (row counts, column schemas, the citywide baseline speed).

The correctness bar: those precomputed values must *equal* what the full
warehouse reports live. Only *when* a value is measured changes -- never what it
is (rule 2: no fabricated numbers).

Skips unless both files exist -- the artifact is built locally from the 12GB
warehouse and neither is in git, so this is local/pre-deploy verification, like
the ~111 other warehouse-gated tests (see .github/workflows/ci.yml).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.services import journey_service, platform_service  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
ARTIFACT_PATH = REPO_ROOT / "data" / "warehouse" / "deployed.duckdb"

pytestmark = pytest.mark.skipif(
    not (WAREHOUSE_PATH.exists() and ARTIFACT_PATH.exists()),
    reason="needs both the full warehouse and a built deployed.duckdb "
    "(run scripts/build_deployed_duckdb.py)",
)


@pytest.fixture
def artifact():
    con = duckdb.connect(str(ARTIFACT_PATH), read_only=True)
    yield con
    con.close()


@pytest.fixture
def warehouse():
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    yield con
    con.close()


@pytest.fixture
def serving_only(monkeypatch):
    """Point the services at the slim artifact, as the deployed container does."""
    monkeypatch.setattr(platform_service, "WAREHOUSE_PATH", ARTIFACT_PATH)


def test_artifact_excludes_raw_and_intermediate_tables(artifact):
    """The whole point of the artifact -- shipping int_trips_enriched would put
    113M rows of training data on the serving host (ADR-005, rule 8)."""
    tables = {row[0] for row in artifact.execute("SHOW TABLES").fetchall()}
    for excluded in ("int_trips_enriched", "stg_trips", "stg_zones", "raw_trips"):
        assert excluded not in tables, f"{excluded} leaked into the serving artifact"
    assert "zone_hourly_demand" in tables
    assert "serving_metadata" in tables


def test_baseline_speed_matches_live_scan(artifact, warehouse):
    """journey_service reads this from metadata instead of scanning 113M rows."""
    precomputed = journey_service._load_baseline_speed(artifact)
    live = journey_service._load_baseline_speed(warehouse)
    assert precomputed == pytest.approx(live, abs=1e-9), (
        f"artifact says {precomputed} mph, full warehouse says {live} mph"
    )


@pytest.mark.parametrize("table", ["int_trips_enriched", "stg_zones"])
def test_precomputed_row_counts_match_live_counts(artifact, warehouse, table):
    """Excluded-table row counts still shown by /warehouse/stats must be the
    real observed counts, not placeholders.

    stg_trips is deliberately not parametrized here: counting it live costs
    ~36s (its row_number() window forces materialization of 113M rows), and it
    shares int_trips_enriched's source rows, which this already covers.
    """
    metadata = platform_service._serving_metadata(artifact)
    from_artifact = platform_service._row_count(artifact, table, metadata)
    from_warehouse = warehouse.execute(f'select count(*) from "{table}"').fetchone()[0]
    assert from_artifact == from_warehouse


def test_warehouse_stats_never_report_a_missing_table(artifact, serving_only):
    """The pre-existing bug this fixes: against a deploy without data/raw,
    stg_trips/stg_zones resolve to read_parquet() over files that aren't there,
    and /warehouse/stats 500s."""
    stats = platform_service.get_warehouse_stats()
    assert set(stats["row_counts"]) == set(platform_service.WAREHOUSE_TABLES)
    assert all(count is not None for count in stats["row_counts"].values()), stats["row_counts"]
    assert stats["total_rows"] > 0


def test_warehouse_tables_expose_columns_for_excluded_tables(artifact, serving_only):
    """/warehouse/tables reports a schema per table -- including the ones the
    artifact no longer physically contains."""
    by_name = {entry["table"]: entry for entry in platform_service.get_warehouse_tables()}
    assert set(by_name) == set(platform_service.WAREHOUSE_TABLES)

    enriched = by_name["int_trips_enriched"]
    assert enriched["row_count"] > 0
    column_names = {column["column_name"] for column in enriched["columns"]}
    assert "avg_speed_mph" in column_names
    assert "pickup_location_id" in column_names


# Every module that opens the warehouse directly. In the deployed image the
# slim artifact simply *is* data/warehouse/nyc_rides.duckdb (see
# backend/Dockerfile), so these all resolve unchanged there -- the patching
# here only simulates that without disturbing the 12GB local file.
WAREHOUSE_READERS = (
    "backend.datasources.nyc_tlc",
    "backend.registry.cities",
    "backend.registry.models",
    "backend.registry.transit",
    "backend.routers.analytics",
    "backend.routers.zones",
    "backend.services.geography_service",
    "backend.services.journey_service",
    "backend.services.model_service",
    "backend.services.platform_service",
    "backend.services.tariff_profiles",
    "backend.services.transit_service",
)


@pytest.fixture
def deployed_like(monkeypatch):
    """Point every warehouse reader at the slim artifact, as the container does."""
    import importlib

    for name in WAREHOUSE_READERS:
        module = importlib.import_module(name)
        monkeypatch.setattr(module, "WAREHOUSE_PATH", ARTIFACT_PATH, raising=True)
    return ARTIFACT_PATH


def test_startup_loaders_succeed_against_the_artifact_alone(deployed_like):
    """The real check behind this whole change: the app must boot with only the
    slim artifact, no 12GB warehouse and no data/raw parquet present.

    Runs the same loaders backend/main.py's lifespan runs, in the same order.
    """
    from backend.registry import cities as cities_registry
    from backend.registry import models as models_registry
    from backend.registry import transit as transit_registry
    from backend.services import model_service, tariff_profiles

    for name, load in (
        ("model_service", model_service.load),
        ("tariff_profiles", tariff_profiles.load),
        ("platform_service", platform_service.load),
        ("journey_service", journey_service.load),
        ("models_registry", models_registry.load),
        ("transit_registry", transit_registry.load),
        ("cities_registry", cities_registry.load),
    ):
        load()  # main.py catches per-loader failures; here a raise is a real failure

    assert journey_service._baseline_speed_mph == pytest.approx(13.40131942095887, abs=1e-9), (
        "baseline speed must survive the switch to the precomputed artifact"
    )
    assert platform_service.get_dashboard_summary()["total_trips"] > 0
    assert len(platform_service.get_hourly_demand_profile()) == 24


def test_artifact_is_materially_smaller_than_the_warehouse():
    """Report the real numbers rather than asserting a magic threshold."""
    artifact_bytes = ARTIFACT_PATH.stat().st_size
    warehouse_bytes = WAREHOUSE_PATH.stat().st_size
    assert artifact_bytes < warehouse_bytes / 10, (
        f"artifact {artifact_bytes:,}B vs warehouse {warehouse_bytes:,}B "
        "-- expected at least a 10x reduction"
    )


if __name__ == "__main__":
    con = duckdb.connect(str(ARTIFACT_PATH), read_only=True)
    print(f"artifact  : {ARTIFACT_PATH.stat().st_size:,} bytes")
    print(f"warehouse : {WAREHOUSE_PATH.stat().st_size:,} bytes")
    print(f"baseline  : {journey_service._load_baseline_speed(con)} mph")
    con.close()
