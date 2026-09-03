"""Correctness tests for the city registry (SPEC-013 FR-4/FR-9): profile
resolution, and capability resolution matching what's actually wired (no
capability claims a route that isn't registered).

The "unknown city_id returns the documented error" test is gone with
ADR-013: no route takes a city id any more, so a client can no longer ask
for a city that doesn't exist. The registry's own missing-row guard is
covered in tests/test_fare_provenance_and_capabilities.py
(`test_capability_matrix_is_none_without_a_registered_city`).
"""
import sys
import uuid
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


@pytest.fixture(scope="module", autouse=True)
def _logged_in(client):
    # /api/profile, /api/capabilities, etc. require login (main.py's
    # _REQUIRE_SESSION). TestClient's cookie jar persists across calls on this
    # shared client instance, so signing up once here covers every test below
    # (same convention as test_api.py).
    email = f"test-{uuid.uuid4()}@example.com"
    resp = client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200, resp.text


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


def test_profile_is_the_registered_city(client):
    """ADR-011/013: this platform serves the one city it has real trip data
    for, and says so from its own seed row rather than a hardcoded literal."""
    resp = client.get("/api/profile")
    assert resp.status_code == 200
    assert resp.json()["id"] == "nyc"


def test_capabilities_match_what_is_actually_wired(client):
    resp = client.get("/api/capabilities")
    assert resp.status_code == 200
    capabilities = resp.json()

    paths = _route_paths(client)
    for capability, route in _CAPABILITY_ROUTES.items():
        if capabilities[capability]:
            assert route in paths, f"capability {capability}=True but no route {route} is registered"

    # area_analysis is asserted against real canonical_areas rows, not a route.
    if capabilities["area_analysis"]:
        areas = client.get("/api/areas").json()
        assert len(areas) > 0


def test_capabilities_backed_by_real_model_registry_rows(client):
    """No capability is hand-authored true -- every True demand/fare/journey
    flag traces back to an active model_registry row."""
    capabilities = client.get("/api/capabilities").json()
    for metric in ("demand", "fare", "journey"):
        resolved = models_registry.resolve_model(metric)
        assert capabilities[metric] == (resolved is not None)


def test_metrics_list_is_subset_of_capabilities(client):
    metrics = client.get("/api/metrics").json()
    capabilities = client.get("/api/capabilities").json()
    assert set(metrics) <= {"demand", "fare", "journey"}
    for m in metrics:
        assert capabilities[m] is True
