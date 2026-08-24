"""Correctness tests for NYCTLCDataSource (SPEC-013 FR-6): every method
returns real mart-backed data; get_trips is not part of the live protocol
(raw trip rows stay dbt/offline-only, rule 8).
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.datasources import get_datasource  # noqa: E402
from backend.datasources.nyc_tlc import NYCTLCDataSource  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def ds() -> NYCTLCDataSource:
    return NYCTLCDataSource()


def test_get_datasource_registry():
    assert isinstance(get_datasource(), NYCTLCDataSource)


def test_get_areas_real_rows(ds):
    areas = ds.get_areas()
    assert len(areas) == 265
    assert {"area_id", "name", "area_type", "latitude", "longitude"} <= areas[0].keys()
    assert "city_id" not in areas[0]  # dropped in ADR-013


def test_get_demand_real_rows(ds):
    rows = ds.get_demand(area_id=132)
    assert len(rows) > 0
    assert all(r["pickup_location_id"] == 132 for r in rows)
    assert all(r["total_trips"] > 0 for r in rows)


def test_get_fares_real_rows(ds):
    rows = ds.get_fares(pickup_area="JFK Airport")
    assert len(rows) > 0
    assert all(r["pickup_zone"] == "JFK Airport" for r in rows)


def test_get_zone_flows_real_rows(ds):
    rows = ds.get_zone_flows(pickup_area="JFK Airport")
    assert len(rows) > 0
    assert all(r["pickup_zone"] == "JFK Airport" for r in rows)


def test_get_temporal_metrics_demand(ds):
    rows = ds.get_temporal_metrics("demand")
    assert len(rows) == 24  # one row per hour of day
    assert all(r["value"] > 0 for r in rows)


def test_get_temporal_metrics_unknown_metric_raises(ds):
    with pytest.raises(KeyError):
        ds.get_temporal_metrics("weather")


def test_get_trips_not_part_of_protocol(ds):
    assert not hasattr(ds, "get_trips")
