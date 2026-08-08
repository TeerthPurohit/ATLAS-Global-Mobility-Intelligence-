"""Correctness tests for geography_service.py's SPEC-013 FR-5 additions
(`list_areas`/`get_area`) and the /api/cities/{city_id}/areas* routes they
back.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402
from backend.services import geography_service  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_list_areas_nyc_matches_zone_count():
    areas = geography_service.list_areas("nyc")
    assert len(areas) == 265
    assert all(a["city_id"] == "nyc" and a["area_type"] == "zone" for a in areas)


def test_list_areas_unknown_city_is_empty():
    assert geography_service.list_areas("atlantis") == []


def test_get_area_known_zone():
    area = geography_service.get_area("nyc", 132)
    assert area is not None
    assert area["name"] == "JFK Airport"
    assert area["latitude"] is not None and area["longitude"] is not None


def test_get_area_unknown_area_id_is_none():
    assert geography_service.get_area("nyc", 999999) is None


def test_resolve_still_works_unchanged():
    """The pre-existing KD-tree resolve() -- a distinct concern from
    list_areas/get_area -- must be untouched by this addition."""
    zone_id = geography_service.resolve(40.758, -73.985)  # Times Square-ish
    assert zone_id is not None
    assert geography_service.resolve(26.9124, 75.7873) is None  # Jaipur, outside coverage


def test_api_list_areas_route(client):
    resp = client.get("/api/cities/nyc/areas")
    assert resp.status_code == 200
    assert len(resp.json()) == 265


def test_api_get_area_route_unknown_city_returns_city_not_found(client):
    resp = client.get("/api/cities/atlantis/areas/1")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "CITY_NOT_FOUND"


def test_api_get_area_route_unknown_area_returns_area_not_found(client):
    resp = client.get("/api/cities/nyc/areas/999999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AREA_NOT_FOUND"
