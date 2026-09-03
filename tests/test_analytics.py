"""Analytics endpoints -- no warehouse required.

`/api/analytics/*` must never 500 and must be driven by real log columns.
The only I/O is the SQLite prediction log, which these tests replace with a
seeded in-memory dict via monkeypatching (same convention as rule 8: no
training data or full-table scans on a request path, and no warehouse either).
"""

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402
from backend.services import prediction_log  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

NOW = datetime.now(timezone.utc)


def _row(offset_minutes: int, city_id: str, fare: float, distance: float) -> dict:
    ts = NOW.replace(minute=5, second=0, microsecond=0) - timedelta(minutes=offset_minutes)
    payload = {
        "city_id": city_id,
        "fare": {"value": fare, "basis": "computed"},
        "distance": {"value": distance, "unit": "miles"},
    }
    return {
        "id": 1,
        "requested_at": ts.isoformat(),
        "city_id": city_id,
        "response_json": json.dumps(payload),
    }


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def _logged_in(client):
    # /api/analytics/* requires login (main.py's _REQUIRE_SESSION). TestClient's
    # cookie jar persists across calls on this shared client instance, so
    # signing up once here covers every test below (same convention as test_api.py).
    email = f"test-{uuid.uuid4()}@example.com"
    resp = client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200, resp.text


def test_summary_empty_history_is_shaped_not_500(client, monkeypatch):
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=50: [])
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_predictions"] == 0
    assert body["cities_served"] == 0
    assert body["date_range"] == {"start": None, "end": None}
    assert body["top_cities"] == []


def test_summary_derives_cities_dates_and_top(client, monkeypatch):
    rows = [
        _row(10, "nyc", 32.5, 8.0),
        _row(20, "nyc", 41.0, 12.0),
        _row(30, "unresolved", 18.0, 5.0),
    ]
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=50: rows)
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_predictions"] == 3
    assert body["cities_served"] == 2
    assert body["date_range"]["start"] is not None and body["date_range"]["end"] is not None
    assert body["top_cities"][0]["city_id"] == "nyc"


def test_summary_tolerates_legacy_response_column(client, monkeypatch):
    rows = [{"id": 1, "requested_at": NOW.isoformat(), "city_id": None, "response_json": None}]
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=50: rows)
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    assert resp.json()["total_predictions"] == 1


def test_trends_buckets_aware_timestamps(client, monkeypatch):
    # Two rows 1 hour apart must land in two different hour buckets, and both
    # must be within the 24h window -- no naive/aware datetime comparison crash.
    rows = [_row(0, "nyc", 30.0, 6.0), _row(60, "nyc", 42.0, 9.0)]
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=10000: rows)
    resp = client.get("/api/analytics/trends", params={"period": "24h"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "24h"
    assert len(body["trends"]["predictions"]) == 2
    # Buckets are returned oldest-first (sorted keys), so the 60-minute-old
    # row precedes the fresh one.
    assert body["trends"]["predictions"] == [1, 1]
    assert body["trends"]["avg_fare"] == [42.0, 30.0]


def test_history_respects_limit_and_offset(client, monkeypatch):
    rows = [_row(i * 10, "nyc", float(i), float(i)) for i in range(5)]
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=50: rows)
    resp = client.get("/api/analytics/history", params={"limit": 2, "offset": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["history"]) == 2
    assert body["limit"] == 2 and body["offset"] == 1


def test_insights_happy_path(client):
    resp = client.get("/api/analytics/insights")
    assert resp.status_code == 200
    assert isinstance(resp.json()["insights"], list)


def test_trends_bad_period_never_500(client, monkeypatch):
    # The frontend only sends 24h/7d/30d, but a typo'd period must degrade
    # to the 24h window -- never a raw 500.
    monkeypatch.setattr(prediction_log, "get_recent_predictions", lambda limit=10000: [])
    resp = client.get("/api/analytics/trends", params={"period": "bogus-period"})
    assert resp.status_code == 200
    assert resp.json()["trends"] == {"predictions": [], "avg_fare": [], "avg_distance": []}
