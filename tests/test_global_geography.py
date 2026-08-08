"""Unit and Integration tests for Atlas Mobility Global Intelligence Engine (Phases 1-4).

Tests place resolution, global city search API, city profile API, and context orchestrator
across NYC, London, Mumbai, Jaipur, Cape Town, Dubai, and Tokyo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402
from backend.services import context_orchestrator, global_geography_service  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── Phase 1: Global Geography Registry ────────────────────────────────────


def test_global_geography_service_registered_cities():
    nyc_prof = global_geography_service.get_city_profile("nyc")
    assert nyc_prof is not None
    assert nyc_prof["city"] == "New York City"
    assert nyc_prof["currency"] == "USD"
    assert nyc_prof["capabilities"]["observed_mobility"] is True

    london_prof = global_geography_service.get_city_profile("london")
    assert london_prof is not None
    assert london_prof["city"] == "London"
    assert london_prof["currency"] == "GBP"
    assert london_prof["capabilities"]["observed_mobility"] is True


def test_global_geography_service_unseen_cities():
    # Mumbai, Jaipur, Dubai, Cape Town, Tokyo should resolve geographic facts
    # with observed_mobility = False (Truth Model discipline)
    mumbai_prof = global_geography_service.get_city_profile("mumbai")
    assert mumbai_prof is not None
    assert mumbai_prof["currency"] == "INR"
    assert mumbai_prof["capabilities"]["observed_mobility"] is False
    assert mumbai_prof["capabilities"]["cross_city_model"] is True

    dubai_prof = global_geography_service.get_city_profile("dubai")
    assert dubai_prof is not None
    assert dubai_prof["currency"] == "AED"
    assert dubai_prof["capabilities"]["observed_mobility"] is False

    capetown_prof = global_geography_service.get_city_profile("cape town")
    assert capetown_prof is not None
    assert capetown_prof["currency"] == "ZAR"
    assert capetown_prof["capabilities"]["observed_mobility"] is False


# ── Phase 2: Global City Search API ───────────────────────────────────────


def test_global_city_search_api(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.geonames_service.search_places",
        lambda q, country=None: [
            {
                "geoname_id": 1275339,
                "name": "Mumbai",
                "country_code": "IN",
                "country_name": "India",
                "latitude": 19.076,
                "longitude": 72.8777,
                "feature_class": "P",
                "feature_code": "PPLA",
                "source": "geonames",
            }
        ] if "mumbai" in q.lower() else []
    )
    resp = client.get("/api/geography/search/global?q=Mumbai")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0

    mumbai = data["results"][0]
    assert "Mumbai" in mumbai["name"]
    assert mumbai["mobility_available"] is False
    assert mumbai["modeling_available"] is True



def test_global_city_search_api_nyc(client):
    resp = client.get("/api/geography/search/global?q=NYC")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert any(r["id"] == "nyc" and r["mobility_available"] is True for r in results)


# ── Phase 3: City Profile API ─────────────────────────────────────────────


def test_city_profile_api_nyc(client):
    resp = client.get("/api/geography/nyc")
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["city"] == "New York City"
    assert profile["currency"] == "USD"
    assert profile["capabilities"]["observed_mobility"] is True
    assert profile["capabilities"]["geographic"] is True


def test_city_profile_api_mumbai(client):
    resp = client.get("/api/geography/mumbai")
    assert resp.status_code == 200
    profile = resp.json()
    assert "Mumbai" in profile["city"]
    assert profile["currency"] == "INR"
    assert profile["capabilities"]["observed_mobility"] is False
    assert profile["capabilities"]["cross_city_model"] is True


def test_city_profile_api_unknown_city_returns_404(client):
    resp = client.get("/api/geography/atlantis-nonexistent-city-xyz")
    assert resp.status_code == 404


# ── Phase 4: Context Orchestrator ─────────────────────────────────────────


def test_context_orchestrator_service():
    ctx = context_orchestrator.get_city_context("nyc")
    assert ctx["city_id"] == "nyc"
    assert "geography" in ctx["context"]
    assert ctx["context"]["geography"]["status"] == "available"
    assert ctx["context"]["geography"]["data"]["city"] == "New York City"

    # Context items must follow envelope structure
    for key, env in ctx["context"].items():
        assert "status" in env
        assert "source" in env
        assert "timestamp" in env
        assert env["status"] in ("available", "unavailable")


def test_context_orchestrator_unseen_city():
    ctx = context_orchestrator.get_city_context("jaipur")
    assert ctx["city_name"].lower() == "jaipur"
    assert "geography" in ctx["context"]
    assert ctx["context"]["geography"]["status"] == "available"
    assert ctx["context"]["geography"]["data"]["currency"] == "INR"
    assert ctx["context"]["mobility_capability"]["data"]["observed_mobility_available"] is False


def test_city_context_api_endpoint(client):
    resp = client.get("/api/geography/london/context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["city_id"] == "london"
    assert "geography" in body["context"]
    assert body["context"]["geography"]["data"]["currency"] == "GBP"


if __name__ == "__main__":
    test_global_geography_service_registered_cities()
    test_global_geography_service_unseen_cities()
    test_context_orchestrator_service()
    test_context_orchestrator_unseen_city()

    from fastapi.testclient import TestClient
    c = TestClient(app)
    test_global_city_search_api(c)
    test_global_city_search_api_nyc(c)
    test_city_profile_api_nyc(c)
    test_city_profile_api_mumbai(c)
    test_city_profile_api_unknown_city_returns_404(c)
    test_city_context_api_endpoint(c)
    print("test_global_geography self-check OK (Phases 1-4 verified)")
