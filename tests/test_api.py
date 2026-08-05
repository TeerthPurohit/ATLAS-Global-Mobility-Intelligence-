"""One happy-path test per backend route (standards.md testing bar)."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # triggers the startup event once
        yield c


def test_predict_demand_happy_path(client):
    resp = client.get("/predict/demand", params={"zone_id": 132, "hour": 8, "day_of_week": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["zone_id"] == 132
    assert body["predicted_demand"] >= 0
    assert body["model"]


def test_predict_fare_happy_path(client):
    resp = client.get("/predict/fare", params={"pickup_zone": 132, "dropoff_zone": 230, "hour": 8})
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_fare"] > 0
    assert body["model"]


def test_list_zones_happy_path(client):
    resp = client.get("/zones")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 200
    assert {"zone_id", "zone", "borough", "latitude", "longitude"} <= body[0].keys()
