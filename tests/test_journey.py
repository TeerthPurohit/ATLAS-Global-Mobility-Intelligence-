"""Correctness tests for POST /journey/estimate (ADR-007)."""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

# Times Square-ish -> JFK-ish, both well inside NYC's zone coverage bbox.
NYC_PICKUP = {"pickup_lat": 40.758, "pickup_lon": -73.985}
NYC_DROPOFF = {"dropoff_lat": 40.6413, "dropoff_lon": -73.7781}
# Jaipur, India -- genuinely outside NYC zone coverage, no snapping.
OUTSIDE_COVERAGE = {"pickup_lat": 26.9124, "pickup_lon": 75.7873}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def _logged_in(client):
    # /journey/estimate requires login (main.py's _REQUIRE_SESSION). TestClient's
    # cookie jar persists across calls on this shared client instance, so
    # signing up once here covers every test below (same convention as test_api.py).
    email = f"test-{uuid.uuid4()}@example.com"
    resp = client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200, resp.text


def _body(pickup=None, dropoff=None, vehicle_type="sedan", departure_time="2024-06-15T08:00:00"):
    payload = {
        **(pickup or NYC_PICKUP),
        **(dropoff or NYC_DROPOFF),
        "departure_time": departure_time,
        "vehicle_type": vehicle_type,
    }
    return payload


def test_journey_estimate_happy_path(client):
    resp = client.post("/journey/estimate", json=_body())
    assert resp.status_code == 200
    body = resp.json()

    top_level_fields = [
        "distance", "duration", "fare", "fare_range", "demand", "carbon_emissions",
        "congestion", "ride_availability", "surge_risk", "best_departure_time",
        "confidence", "ai_recommendation",
    ]
    for field in top_level_fields:
        assert field in body, f"missing field {field}"
        entry = body[field]
        assert entry["basis"] in ("computed", "modeled_estimate", "unavailable")
        if entry["basis"] != "computed":
            assert entry["reason"], f"{field} has basis={entry['basis']} but no reason"

    # Real NYC pickup/dropoff -> the core numeric fields must actually resolve.
    assert body["distance"]["basis"] == "computed"
    # Total fare honestly inherits "modeled_estimate" once any adjustment term
    # (traffic/weather/demand) is a modeled_estimate -- base_fare itself, the
    # XGBoost model's own prediction, must be "computed".
    assert body["fare"]["basis"] in ("computed", "modeled_estimate")
    assert body["fare"]["value"] > 0
    assert isinstance(body["fare_breakdown"], dict) and "base_fare" in body["fare_breakdown"]
    assert body["fare_breakdown"]["base_fare"]["basis"] == "computed"
    # Regression: fare_range must not be "unavailable" just because the fare
    # total is "modeled_estimate" (it inherits basis, doesn't require exact
    # basis=="computed" -- a real bug caught by hitting a live server).
    assert body["fare_range"]["basis"] != "unavailable"
    assert "-" in body["fare_range"]["value"]


def test_journey_estimate_outside_coverage_degrades_honestly(client):
    resp = client.post("/journey/estimate", json=_body(pickup=OUTSIDE_COVERAGE))
    assert resp.status_code == 200
    body = resp.json()

    # Zone-keyed fields have no data for Jaipur -- unavailable, not a crash,
    # not a fabricated number (the "degrade honestly" design principle).
    assert body["fare"]["basis"] == "unavailable"
    assert body["demand"]["basis"] == "unavailable"
    assert body["confidence"]["value"] < 100


def test_journey_estimate_vehicle_type_changes_fare_and_carbon(client):
    sedan = client.post("/journey/estimate", json=_body(vehicle_type="sedan")).json()
    suv = client.post("/journey/estimate", json=_body(vehicle_type="suv")).json()

    assert sedan["fare"]["value"] != suv["fare"]["value"]
    assert sedan["carbon_emissions"]["value"] != suv["carbon_emissions"]["value"]
    assert suv["carbon_emissions"]["value"] > sedan["carbon_emissions"]["value"]


def test_journey_estimate_unknown_vehicle_type_is_unavailable_not_default(client):
    resp = client.post("/journey/estimate", json=_body(vehicle_type="hovercraft"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["carbon_emissions"]["basis"] == "unavailable"
    assert body["carbon_emissions"]["reason"]


def test_journey_narrative_grounding(client):
    resp = client.post("/journey/estimate", json=_body())
    body = resp.json()
    rec = body["ai_recommendation"]
    assert rec["basis"] in ("modeled_estimate", "unavailable")
    if rec["basis"] == "modeled_estimate":
        assert rec["value"]
