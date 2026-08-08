"""Correctness tests for the geography-discovery layer (GeoNames client,
Google Places fallback, geography router). Every test here mocks HTTP --
these must never make a live GeoNames call. See test_geonames_live_smoke
for the one manual-only integration check (opt-in via GEONAMES_LIVE_TEST=1).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.errors_geography import GeographyError, GeographyErrorCode  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.geography import _classify_feature, _hierarchy_type  # noqa: E402
from backend.services import geonames_service  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"


@pytest.fixture(autouse=True)
def _isolated_service_state(monkeypatch):
    """Every test gets a configured username and empty caches, regardless of
    call order -- lru_cache state otherwise leaks between tests."""
    monkeypatch.setattr(geonames_service, "_USERNAME", "test_user")
    geonames_service.get_all_countries.cache_clear()
    geonames_service._search_geonames_cached.cache_clear()
    geonames_service.get_children.cache_clear()
    geonames_service.get_hierarchy.cache_clear()
    geonames_service._reverse_country_cached.cache_clear()
    geonames_service._get_timezone_cached.cache_clear()
    yield


def _fake_response(json_body, status_code: int = 200):
    return SimpleNamespace(status_code=status_code, json=lambda: json_body)


@pytest.fixture
def client():
    if not WAREHOUSE_PATH.exists():
        pytest.skip("warehouse not built")
    with TestClient(app) as c:
        yield c


# ── Auth configuration ──────────────────────────────────────────────────


def test_missing_username_raises_unavailable(monkeypatch):
    monkeypatch.setattr(geonames_service, "_USERNAME", "")
    with pytest.raises(GeographyError) as exc_info:
        geonames_service.get_all_countries()
    assert exc_info.value.code == GeographyErrorCode.GEONAMES_UNAVAILABLE


def test_credentials_never_leak_in_error_message(monkeypatch):
    monkeypatch.setattr(geonames_service, "_USERNAME", "super_secret_user")
    monkeypatch.setattr(
        geonames_service.httpx, "get",
        lambda *a, **k: _fake_response({"status": {"message": "user does not exist.", "value": 10}}, 401),
    )
    with pytest.raises(GeographyError) as exc_info:
        geonames_service.get_all_countries()
    assert "super_secret_user" not in str(exc_info.value)
    assert "super_secret_user" not in exc_info.value.message


# ── Response parsing ────────────────────────────────────────────────────


def test_country_info_parsing(monkeypatch):
    body = {
        "geonames": [
            {
                "geonameId": 6252001, "countryCode": "US", "isoAlpha3": "USA",
                "countryName": "United States", "capital": "Washington", "continent": "NA",
                "north": "49.38", "south": "24.52", "east": "-66.95", "west": "-125.0",
            }
        ]
    }
    monkeypatch.setattr(geonames_service.httpx, "get", lambda *a, **k: _fake_response(body))
    countries = geonames_service.get_all_countries()
    assert len(countries) == 1
    c = countries[0]
    assert c["iso2"] == "US"
    assert c["name"] == "United States"
    assert c["latitude"] == pytest.approx((49.38 + 24.52) / 2)
    assert c["longitude"] == pytest.approx((-66.95 + -125.0) / 2)


def test_search_requests_populated_places_and_normalizes(monkeypatch):
    captured = {}
    body = {
        "geonames": [
            {
                "geonameId": 1275339, "name": "Mumbai", "countryCode": "IN", "countryName": "India",
                "adminCode1": "16", "adminName1": "Maharashtra", "fcl": "P", "fcode": "PPLA",
                "lat": "19.07283", "lng": "72.88261",
            }
        ]
    }

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return _fake_response(body)

    monkeypatch.setattr(geonames_service.httpx, "get", fake_get)
    results = geonames_service.search_places("Mumbai")
    assert captured["params"]["featureClass"] == "P"
    assert len(results) == 1
    assert results[0] == {
        "geoname_id": 1275339, "name": "Mumbai", "country_code": "IN", "country_name": "India",
        "admin1_code": "16", "admin1_name": "Maharashtra", "feature_class": "P", "feature_code": "PPLA",
        "latitude": pytest.approx(19.07283), "longitude": pytest.approx(72.88261), "source": "geonames",
    }


def test_search_falls_back_to_google_places_when_geonames_unavailable(monkeypatch):
    monkeypatch.setattr(
        geonames_service.httpx, "get",
        lambda *a, **k: _fake_response({"status": {"message": "user does not exist.", "value": 10}}, 401),
    )
    monkeypatch.setattr(
        geonames_service.google_places_service, "search",
        lambda q, country=None: [
            {"geoname_id": None, "name": "Mumbai", "country_code": "IN", "country_name": "India",
             "admin1_code": None, "admin1_name": None, "feature_class": None, "feature_code": None,
             "latitude": 19.07, "longitude": 72.88, "source": "google_places"}
        ],
    )
    results = geonames_service.search_places("Mumbai")
    assert len(results) == 1
    assert results[0]["source"] == "google_places"


def test_children_classification_helper():
    assert _classify_feature("A") == "administrative_division"
    assert _classify_feature("P") == "populated_place"
    assert _classify_feature("H") == "other"
    assert _classify_feature(None) == "other"


def test_hierarchy_type_classification_helper():
    assert _hierarchy_type(None, "CONT") == "continent"
    assert _hierarchy_type(None, "PCLI") == "country"
    assert _hierarchy_type(None, "ADM1") == "admin1"
    assert _hierarchy_type(None, "ADM2") == "admin2"
    assert _hierarchy_type("P", "PPL") == "city"
    assert _hierarchy_type("H", "STM") == "place"


def test_hierarchy_parsing(monkeypatch):
    body = {
        "geonames": [
            {"geonameId": 6255149, "name": "Asia", "fcl": "L", "fcode": "CONT"},
            {"geonameId": 1269750, "name": "India", "fcl": "A", "fcode": "PCLI"},
            {"geonameId": 1264714, "name": "Maharashtra", "fcl": "A", "fcode": "ADM1"},
            {"geonameId": 1275339, "name": "Mumbai", "fcl": "P", "fcode": "PPLA", "lat": "19.07", "lng": "72.88"},
        ]
    }
    monkeypatch.setattr(geonames_service.httpx, "get", lambda *a, **k: _fake_response(body))
    nodes = geonames_service.get_hierarchy(1275339)
    assert [n["name"] for n in nodes] == ["Asia", "India", "Maharashtra", "Mumbai"]
    assert nodes[-1]["latitude"] == pytest.approx(19.07)


def test_reverse_geocoding_parsing(monkeypatch):
    body = {"countryCode": "IN", "countryName": "India", "adminCode1": "16", "adminName1": "Maharashtra"}
    monkeypatch.setattr(geonames_service.httpx, "get", lambda *a, **k: _fake_response(body))
    result = geonames_service.reverse_country(19.07, 72.88)
    assert result == {"country_code": "IN", "country_name": "India", "admin1_code": "16", "admin1_name": "Maharashtra"}


def test_timezone_parsing(monkeypatch):
    body = {"timezoneId": "Asia/Kolkata", "countryCode": "IN"}
    monkeypatch.setattr(geonames_service.httpx, "get", lambda *a, **k: _fake_response(body))
    result = geonames_service.get_timezone(19.07, 72.88)
    assert result == {"timezone_id": "Asia/Kolkata"}


# ── Error handling ──────────────────────────────────────────────────────


def test_geonames_auth_error_maps_to_auth_failed(monkeypatch):
    monkeypatch.setattr(
        geonames_service.httpx, "get",
        lambda *a, **k: _fake_response({"status": {"message": "user does not exist.", "value": 10}}, 401),
    )
    with pytest.raises(GeographyError) as exc_info:
        geonames_service.get_children(6252001)
    assert exc_info.value.code == GeographyErrorCode.GEONAMES_AUTH_FAILED
    assert "user does not exist" not in exc_info.value.message


def test_geonames_rate_limit_maps_to_rate_limited(monkeypatch):
    monkeypatch.setattr(
        geonames_service.httpx, "get",
        lambda *a, **k: _fake_response({"status": {"message": "the hourly limit was exceeded.", "value": 19}}, 403),
    )
    with pytest.raises(GeographyError) as exc_info:
        geonames_service.get_hierarchy(5128581)
    assert exc_info.value.code == GeographyErrorCode.GEONAMES_RATE_LIMITED


def test_invalid_json_response_raises_unavailable(monkeypatch):
    def fake_get(*a, **k):
        def _raise():
            raise ValueError("bad json")
        return SimpleNamespace(status_code=200, json=_raise)

    monkeypatch.setattr(geonames_service.httpx, "get", fake_get)
    with pytest.raises(GeographyError) as exc_info:
        geonames_service.get_all_countries()
    assert exc_info.value.code == GeographyErrorCode.GEONAMES_UNAVAILABLE


def test_timeout_raises_unavailable(monkeypatch):
    import httpx as httpx_module

    def fake_get(*a, **k):
        raise httpx_module.TimeoutException("timed out")

    monkeypatch.setattr(geonames_service.httpx, "get", fake_get)
    with pytest.raises(GeographyError) as exc_info:
        geonames_service.get_children(1)
    assert exc_info.value.code == GeographyErrorCode.GEONAMES_UNAVAILABLE


# ── Caching ──────────────────────────────────────────────────────────────


def test_caching_avoids_repeated_geonames_calls(monkeypatch):
    call_count = {"n": 0}
    body = {
        "geonames": [
            {"geonameId": 6252001, "countryCode": "US", "countryName": "United States", "isoAlpha3": "USA",
             "capital": "Washington", "continent": "NA", "north": "49", "south": "25", "east": "-67", "west": "-125"}
        ]
    }

    def fake_get(*a, **k):
        call_count["n"] += 1
        return _fake_response(body)

    monkeypatch.setattr(geonames_service.httpx, "get", fake_get)
    geonames_service.get_all_countries()
    geonames_service.get_all_countries()
    geonames_service.get_all_countries()
    assert call_count["n"] == 1


# ── NYC mapping ─────────────────────────────────────────────────────────


def test_api_search_new_york_shows_mobility_support(client, monkeypatch):
    monkeypatch.setattr(
        geonames_service, "search_places",
        lambda q, country=None: [
            {"geoname_id": 5128581, "name": "New York City", "country_code": "US", "country_name": "United States",
             "admin1_code": "NY", "admin1_name": "New York", "feature_class": "P", "feature_code": "PPL",
             "latitude": 40.71, "longitude": -74.0, "source": "geonames"}
        ],
    )
    resp = client.get("/api/geography/search", params={"q": "New York"})
    body = resp.json()["results"][0]
    assert body["mobility_support"] == {"supported": True, "city_id": "nyc"}


def test_api_search_unsupported_city_marked_unsupported(client, monkeypatch):
    monkeypatch.setattr(
        geonames_service, "search_places",
        lambda q, country=None: [
            {"geoname_id": 2643743, "name": "London", "country_code": "GB", "country_name": "United Kingdom",
             "admin1_code": None, "admin1_name": None, "feature_class": "P", "feature_code": "PPLC",
             "latitude": 51.5, "longitude": -0.12, "source": "geonames"}
        ],
    )
    resp = client.get("/api/geography/search", params={"q": "London"})
    body = resp.json()["results"][0]
    assert body["mobility_support"] == {"supported": False, "city_id": None}


# ── Router / API-level ──────────────────────────────────────────────────


def test_api_countries_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        geonames_service, "get_all_countries",
        lambda: [{"geoname_id": 6252001, "iso2": "US", "iso3": "USA", "name": "United States",
                   "capital": "Washington", "continent": "NA", "latitude": 37.0, "longitude": -96.0}],
    )
    resp = client.get("/api/geography/countries")
    assert resp.status_code == 200
    body = resp.json()["countries"][0]
    assert body["iso2"] == "US"
    assert body["supported"] is True


def test_api_country_places_unknown_country_returns_404(client, monkeypatch):
    monkeypatch.setattr(geonames_service, "get_country_geoname_id", lambda code: None)
    resp = client.get("/api/geography/countries/ZZ/places")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "COUNTRY_NOT_FOUND"


def test_api_hierarchy_unknown_place_returns_404(client, monkeypatch):
    monkeypatch.setattr(geonames_service, "get_hierarchy", lambda geoname_id: [])
    resp = client.get("/api/geography/places/999999999/hierarchy")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PLACE_NOT_FOUND"


def test_api_reverse_invalid_coordinates_returns_400(client):
    resp = client.get("/api/geography/reverse", params={"lat": 999, "lng": 0})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_COORDINATES"


def test_api_reverse_happy_path(client, monkeypatch):
    monkeypatch.setattr(
        geonames_service, "reverse_country",
        lambda lat, lng: {"country_code": "IN", "country_name": "India", "admin1_code": "16", "admin1_name": "Maharashtra"},
    )
    resp = client.get("/api/geography/reverse", params={"lat": 19.07, "lng": 72.88})
    assert resp.status_code == 200
    assert resp.json()["country_code"] == "IN"


def test_api_geonames_unavailable_returns_structured_error(client, monkeypatch):
    def _raise():
        raise GeographyError(
            GeographyErrorCode.GEONAMES_UNAVAILABLE, "Geographic discovery is temporarily unavailable.", 503
        )

    monkeypatch.setattr(geonames_service, "get_all_countries", _raise)
    resp = client.get("/api/geography/countries")
    assert resp.status_code == 503
    assert resp.json() == {
        "error": {"code": "GEONAMES_UNAVAILABLE", "message": "Geographic discovery is temporarily unavailable."}
    }


# ── Backward compatibility ──────────────────────────────────────────────


def test_existing_zones_endpoint_unaffected(client):
    resp = client.get("/zones")
    assert resp.status_code == 200


def test_existing_predict_demand_endpoint_unaffected(client):
    resp = client.get("/predict/demand", params={"zone_id": 132, "hour": 8, "day_of_week": 1})
    assert resp.status_code in (200, 400)  # 400 only if that zone genuinely has no momentum history


# ── Live smoke test (manual only) ───────────────────────────────────────


@pytest.mark.skipif(
    os.environ.get("GEONAMES_LIVE_TEST") != "1",
    reason="set GEONAMES_LIVE_TEST=1 to run against the real GeoNames API (requires a working GEONAMES_USERNAME)",
)
def test_geonames_live_smoke():
    countries = geonames_service.get_all_countries()
    assert len(countries) > 50
    assert any(c["iso2"] == "US" for c in countries)
