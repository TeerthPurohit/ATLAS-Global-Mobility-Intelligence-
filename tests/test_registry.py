"""Correctness tests for the Global Mobility Domain Model registry
(SPEC-013 FR-4/FR-9): country/city listing, capability resolution matches
what's actually wired (no city claims a capability with no backing route),
unsupported city/country returns the documented error, not a 200 with fake
data.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402
from backend.registry import models as models_registry  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

# capability -> a real route that must exist on the live app if that
# capability is True (this is the "verified by test, not hand-authored
# trust" check the spec's acceptance criteria calls for).
_CAPABILITY_ROUTES = {
    "demand": "/predict/demand",
    "fare": "/predict/fare",
    "journey": "/journey/estimate",
    "chat": "/chat",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _route_paths(client) -> set[str]:
    """Flat set of every registered path. Recent FastAPI wraps
    `app.include_router(...)` results as a lazy `_IncludedRouter` rather than
    flattening sub-routes into `app.routes` directly -- walk
    `original_router.routes` to see the real, live-mounted routes."""
    paths: set[str] = set()
    for route in client.app.routes:
        if (p := getattr(route, "path", None)):
            paths.add(p)
        elif (original := getattr(route, "original_router", None)) is not None:
            paths.update(p for sub in original.routes if (p := getattr(sub, "path", None)))
    return paths


def test_list_countries_includes_us(client):
    resp = client.get("/api/countries")
    assert resp.status_code == 200
    countries = resp.json()["countries"]
    us = next((c for c in countries if c["iso_code"] == "US"), None)
    assert us is not None
    assert us["supported"] is True
    assert us["supported_city_count"] >= 1


def test_list_country_cities_nyc(client):
    resp = client.get("/api/countries/US/cities")
    assert resp.status_code == 200
    cities = resp.json()
    assert any(c["id"] == "nyc" for c in cities)


def test_unsupported_country_returns_documented_error_not_fake_data(client):
    resp = client.get("/api/countries/ZZ")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "COUNTRY_NOT_SUPPORTED"


def test_unknown_city_returns_documented_error_not_fake_data(client):
    resp = client.get("/api/cities/atlantis")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "CITY_NOT_FOUND"


def test_capabilities_match_what_is_actually_wired(client):
    resp = client.get("/api/cities/nyc/capabilities")
    assert resp.status_code == 200
    capabilities = resp.json()

    paths = _route_paths(client)
    for capability, route in _CAPABILITY_ROUTES.items():
        if capabilities[capability]:
            assert route in paths, f"capability {capability}=True but no route {route} is registered"

    # area_analysis is asserted against real canonical_areas rows, not a route.
    if capabilities["area_analysis"]:
        areas = client.get("/api/cities/nyc/areas").json()
        assert len(areas) > 0


def test_capabilities_backed_by_real_model_registry_rows(client):
    """No capability is hand-authored true -- every True demand/fare/journey
    flag traces back to an active model_registry row."""
    resp = client.get("/api/cities/nyc/capabilities")
    capabilities = resp.json()
    for metric in ("demand", "fare", "journey"):
        resolved = models_registry.resolve_model("nyc", metric)
        assert capabilities[metric] == (resolved is not None)


def test_metrics_list_is_subset_of_capabilities(client):
    metrics = client.get("/api/cities/nyc/metrics").json()
    capabilities = client.get("/api/cities/nyc/capabilities").json()
    assert set(metrics) <= {"demand", "fare", "journey"}
    for m in metrics:
        assert capabilities[m] is True


def test_london_capabilities_reflect_cycle_share_mode(client):
    resp = client.get("/api/cities/london/capabilities")
    assert resp.status_code == 200
    capabilities = resp.json()
    assert capabilities["mobility_mode"] == "cycle_share"
    assert capabilities["area_type"] == "cycle_station"
    assert capabilities["demand"] is True
    assert capabilities["fare"] is False
    # journey_predictors.py orchestrates routing/demand/fare/carbon/congestion/
    # availability/surge/best_departure with honest per-component degradation
    # for ANY city -- it was never actually London-specific. This capability
    # flag used to gate on a model_registry row that only ever existed for
    # nyc (a seed-data gap, not a real capability gap: /journey/estimate
    # already worked for London in production, same as every other city).
    # Fixed via /debug 2026-08-13 alongside extending availability/surge/
    # best_departure to WorldMove-covered cities.
    assert capabilities["journey"] is True
