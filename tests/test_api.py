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


def test_predict_demand_negative_raw_pred_falls_back_to_ewma(client):
    # Low volume zone's frozen momentum snapshot pushes XGBoost negative --
    # assert the response is a positive EWMA estimate, not the old flat 0.0 clamp,
    # and that the fallback is honestly labeled.
    resp = client.get("/predict/demand", params={"zone_id": 2, "hour": 8, "day_of_week": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_demand"] > 0
    assert body["model"] == "ewma_fallback_v1"



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


def test_post_chat_and_history(client):
    # Turn 1
    resp = client.post("/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "session_id" in body
    session_id = body["session_id"]

    # History retrieval
    hist_resp = client.get(f"/chat/history/{session_id}")
    assert hist_resp.status_code == 200
    messages = hist_resp.json()
    assert len(messages) == 2  # user prompt + assistant answer
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_chat_history_404(client):
    resp = client.get("/chat/history/non_existent_session_99999")
    assert resp.status_code == 404


def test_websocket_chat_stream(client):
    with client.websocket_connect("/chat/stream") as websocket:
        websocket.send_json({"question": "What is the average fare for trips in JFK Airport?"})
        received = []
        while True:
            try:
                data = websocket.receive_json()
                received.append(data)
                if data.get("type") == "done":
                    break
            except Exception:
                break
        assert len(received) >= 1
        assert received[-1]["type"] == "done"


# ── Global Mobility Domain Model (SPEC-013) -- one happy-path test per new endpoint ──


def test_list_countries_happy_path(client):
    resp = client.get("/api/countries")
    assert resp.status_code == 200
    assert any(c["iso_code"] == "US" for c in resp.json()["countries"])


def test_get_country_happy_path(client):
    resp = client.get("/api/countries/US")
    assert resp.status_code == 200
    assert resp.json() == {"iso_code": "US", "name": "United States", "supported": True, "supported_city_count": 1}


def test_list_country_cities_happy_path(client):
    resp = client.get("/api/countries/US/cities")
    assert resp.status_code == 200
    assert any(c["id"] == "nyc" for c in resp.json())


def test_get_city_happy_path(client):
    resp = client.get("/api/cities/nyc")
    assert resp.status_code == 200
    assert resp.json()["id"] == "nyc"


def test_get_city_capabilities_happy_path(client):
    resp = client.get("/api/cities/nyc/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["demand"] is True and body["fare"] is True


def test_list_city_areas_happy_path(client):
    resp = client.get("/api/cities/nyc/areas")
    assert resp.status_code == 200
    assert len(resp.json()) == 265


def test_get_city_area_happy_path(client):
    resp = client.get("/api/cities/nyc/areas/132")
    assert resp.status_code == 200
    assert resp.json()["name"] == "JFK Airport"


def test_list_city_metrics_happy_path(client):
    resp = client.get("/api/cities/nyc/metrics")
    assert resp.status_code == 200
    assert "demand" in resp.json()


def test_city_predict_demand_happy_path(client):
    resp = client.post("/api/cities/nyc/predict/demand", json={"area_id": 132, "hour": 8, "day_of_week": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["prediction"] >= 0
    assert body["city_id"] == "nyc"


def test_city_predict_fare_happy_path(client):
    resp = client.post("/api/cities/nyc/predict/fare", json={"pickup_area_id": 132, "dropoff_area_id": 230, "hour": 8})
    assert resp.status_code == 200
    assert resp.json()["prediction"] > 0


def test_city_forecast_happy_path(client):
    resp = client.get("/api/cities/nyc/forecast")
    assert resp.status_code == 200
    assert len(resp.json()["series"]) == 24


def test_city_chat_happy_path(client):
    resp = client.post("/api/cities/nyc/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["city_id"] == "nyc"
    assert body["answer"]


def test_unknown_city_id_returns_404_error_response(client):
    resp = client.get("/api/cities/atlantis")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "CITY_NOT_FOUND"


# ── Backward compatibility (SPEC-013 NFR): every pre-existing endpoint's ──
# request/response shape and behavior is unchanged by this phase's additions.


def test_backward_compat_predict_demand(client):
    resp = client.get("/predict/demand", params={"zone_id": 132, "hour": 8, "day_of_week": 1})
    assert resp.status_code == 200
    assert resp.json().keys() == {"zone_id", "hour", "day_of_week", "predicted_demand", "model"}


def test_backward_compat_predict_fare(client):
    resp = client.get("/predict/fare", params={"pickup_zone": 132, "dropoff_zone": 230, "hour": 8})
    assert resp.status_code == 200
    assert resp.json().keys() == {"pickup_zone", "dropoff_zone", "hour", "predicted_fare", "model"}


def test_backward_compat_zones(client):
    resp = client.get("/zones")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 200
    assert body[0].keys() == {"zone_id", "zone", "borough", "service_zone", "latitude", "longitude"}


def test_backward_compat_chat_original_fields_present_and_unchanged(client):
    # ChatRequest/ChatResponse additively gained optional city_id/area_id
    # (FR-11) -- the original fields must still be present with the same
    # meaning; omitting the new fields entirely must still work.
    resp = client.post("/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?"})
    assert resp.status_code == 200
    body = resp.json()
    assert {"answer", "route", "sql", "session_id"} <= body.keys()
    assert isinstance(body["answer"], str) and body["answer"]


def test_backward_compat_journey_estimate(client):
    resp = client.post(
        "/journey/estimate",
        json={
            "pickup_lat": 40.758, "pickup_lon": -73.985,
            "dropoff_lat": 40.6413, "dropoff_lon": -73.7781,
            "departure_time": "2024-06-15T08:00:00", "vehicle_type": "sedan",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.keys() == {
        "distance", "duration", "fare", "fare_range", "demand", "carbon_emissions",
        "congestion", "ride_availability", "surge_risk", "best_departure_time",
        "confidence", "fare_breakdown", "ai_recommendation",
    }
    assert body["fare"]["value"] > 0
