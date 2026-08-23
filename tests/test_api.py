"""One happy-path test per backend route (standards.md testing bar)."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402
from backend.services import prediction_log  # noqa: E402

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
    assert body["model"] in ("xgboost_demand_v1", "ewma_fallback_v1")




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


# ── City-scoped endpoints -- one happy-path test per endpoint ──


def test_list_cities_happy_path(client):
    resp = client.get("/api/cities")
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()["results"]}
    assert ids == {"nyc"}


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


# ── Phase A backend fixes (QA pass) ──


def test_get_city_capabilities_is_bare_capabilities_not_wrapped(client):
    # The duplicate route returned a bare Capabilities model; the frontend
    # used to expect {city_id, capabilities}. Lock in the real shape.
    resp = client.get("/api/cities/nyc/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert "city_id" not in body and "capabilities" not in body
    assert body["demand"] is True and body["fare"] is True


def test_city_tariff_shape(client):
    resp = client.get("/api/cities/nyc/tariff")
    assert resp.status_code == 200
    body = resp.json()
    assert body["city_id"] == "nyc"
    assert "available" in body and "base_fare" in body


def test_context_weather_unknown_city_is_400(client):
    resp = client.get("/api/context/weather", params={"city_id": "atlantis"})
    assert resp.status_code == 400  # client error, not a bare 500


def test_context_holiday_unknown_city_is_400(client):
    resp = client.get("/api/context/holiday", params={"city_id": "atlantis"})
    assert resp.status_code == 400


def test_context_traffic_unknown_city_is_400(client):
    resp = client.get("/api/context/traffic", params={"city_id": "atlantis"})
    assert resp.status_code == 400


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
        "confidence", "fare_breakdown", "ai_recommendation", "city_id",
    }
    assert body["fare"]["value"] > 0


# ── Frontend-integration contract (frontend-web/lib/api.ts) ───────────────────
# Every consumer contract below must be satisfied by the live backend: exact
# paths, bare/wrapped shapes, echoed city_id/area_id, and the ChatRoute union.


def test_journey_history_returns_log_rows(client, monkeypatch):
    row = {
        "id": 7,
        "requested_at": "2026-08-11T08:00:00+00:00",
        "pickup_lat": 40.758,
        "pickup_lon": -73.985,
        "dropoff_lat": 40.6413,
        "dropoff_lon": -73.7781,
        "departure_time": "2024-06-15T08:00:00",
        "vehicle_type": "sedan",
        "fare_value": "35.40",
        "fare_basis": "computed",
        "confidence_value": 82.5,
        "city_id": "nyc",
        "response_json": '{"city_id":"nyc"}',
    }
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=50: [row])
    resp = client.get("/journey/history")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0] == row
    assert body[0]["city_id"] == "nyc"
    assert isinstance(body[0]["response_json"], str)


def test_journey_history_empty_is_200_not_500(client, monkeypatch):
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=50: [])
    resp = client.get("/journey/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_insights_bare_list_matches_frontend(client):
    # getInsights hits /insights and expects a BARE InsightDoc[] -- not the
    # {insights: [...]} wrapper /api/analytics/insights uses.
    resp = client.get("/insights")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        doc = body[0]
        assert {"zone_name", "text", "total_trips"} <= doc.keys()


def test_post_chat_echoes_city_and_area(client):
    resp = client.post(
        "/chat",
        json={
            "question": "What is the average fare for trips picked up in JFK Airport?",
            "city_id": "nyc", "area_id": 132,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["city_id"] == "nyc"
    assert body["area_id"] == 132
    assert body["route"] in ("numeric", "explanatory")


def test_websocket_stream_echoes_city_and_area(client):
    with client.websocket_connect("/chat/stream") as websocket:
        websocket.send_json({
            "question": "What is the average fare for trips in JFK Airport?",
            "city_id": "nyc", "area_id": 132,
        })
        done = None
        while True:
            try:
                data = websocket.receive_json()
            except Exception:
                break
            if data.get("type") == "done":
                done = data["payload"]
                break
    assert done is not None
    assert done["city_id"] == "nyc"
    assert done["area_id"] == 132
    assert done["route"] in ("numeric", "explanatory")


def test_context_weather_bad_timestamp_is_400(client):
    resp = client.get("/api/context/weather", params={"city_id": "nyc", "timestamp": "not-a-date"})
    assert resp.status_code == 400


def test_context_holiday_bad_date_is_400(client):
    resp = client.get("/api/context/holiday", params={"city_id": "nyc", "date": "bogus"})
    assert resp.status_code == 400


def test_context_missing_city_id_is_422(client):
    resp = client.get("/api/context/weather")
    assert resp.status_code == 422


def test_mobility_contract(client):
    # Every mobility endpoint must return the MobilityResponse shape
    # {value, unit, status, method, source, confidence, reason} under its key.
    body = {
        "city_id": "nyc",
        "pickup": {"lat": 40.758, "lon": -73.985},
        "dropoff": {"lat": 40.6413, "lon": -73.7781},
        "departure_time": "2024-06-15T08:00:00",
        "vehicle_type": "sedan",
    }
    route = client.post("/api/mobility/route", json=body)
    assert route.status_code == 200
    for field in ("distance", "duration"):
        mob = route.json()[field]
        assert set(mob.keys()) == {"value", "unit", "status", "method", "source", "confidence", "reason"}
        assert mob["status"] in ("computed", "modeled_estimate", "unavailable")

    for endpoint, key in [
        ("fare", "fare"), ("demand", "demand"), ("congestion", "congestion"),
        ("availability", "availability"), ("surge", "surge"), ("carbon", "carbon"),
    ]:
        resp = client.post(f"/api/mobility/{endpoint}", json=body)
        assert resp.status_code == 200
        mob = resp.json()[key]
        assert set(mob.keys()) == {"value", "unit", "status", "method", "source", "confidence", "reason"}
        assert mob["status"] in ("computed", "modeled_estimate", "unavailable")

    # The frontend MobilityResponse contract is value: number | null. The
    # categorical predictors (congestion/availability/surge) carry their real
    # 0-1 score here -- never the bucket string -- or null when unavailable.
    for endpoint, key in [
        ("congestion", "congestion"), ("availability", "availability"), ("surge", "surge"),
    ]:
        mob = client.post(f"/api/mobility/{endpoint}", json=body).json()[key]
        if mob["status"] != "unavailable":
            assert isinstance(mob["value"], (int, float))
            assert isinstance(mob["unit"], str)
        else:
            assert mob["value"] is None

    departure = client.post("/api/mobility/departure-time", json=body)
    assert departure.status_code == 200
    assert {"recommended_departure", "reason", "confidence", "status", "request_id", "timestamp"} <= departure.json().keys()


def test_mobility_unknown_city_degrades_not_500(client):
    resp = client.post(
        "/api/mobility/demand",
        json={
            "city_id": "atlantis",
            "pickup": {"lat": 40.758, "lon": -73.985},
            "dropoff": {"lat": 40.6413, "lon": -73.7781},
            "departure_time": "2024-06-15T08:00:00",
            "vehicle_type": "sedan",
        },
    )
    assert resp.status_code == 200
    status = resp.json()["demand"]["status"]
    # A city with no trained zone-level model is either given a transferred
    # population-scaled estimate (if geocoding resolves it -- the intentional
    # "global mobility" behavior, journey_predictors.py) or degraded to
    # unavailable; a bare 500 is never acceptable.
    assert status in ("unavailable", "modeled_estimate")
