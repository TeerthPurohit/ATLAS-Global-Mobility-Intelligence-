from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.registry import global_cities  # noqa: E402


def test_get_city_registered():
    global_cities.load()
    nyc = global_cities.get_city("nyc")
    assert nyc is not None
    assert nyc["model_status"] == "OBSERVED"
    assert nyc["population_source"] == "registered"


def test_get_city_worldmove():
    global_cities.load()
    jaipur = global_cities.get_city("IN_JAIPUR")
    assert jaipur is not None
    assert jaipur["model_status"] == "TRANSFER"
    assert jaipur["worldmove_available"] is True


def test_get_city_unknown_returns_none():
    global_cities.load()
    assert global_cities.get_city("nonexistent_xyz") is None


def test_find_by_name_case_insensitive():
    global_cities.load()
    found = global_cities.find_by_name("jaipur", "IN")
    assert found is not None
    assert found["city_id"] == "IN_JAIPUR"
    assert global_cities.find_by_name("Nonexistentville", "ZZ") is None


def test_list_cities_filters_by_tier():
    global_cities.load()
    observed = global_cities.list_cities(model_status="OBSERVED")
    assert len(observed) == 2
    assert {c["city_id"] for c in observed} == {"nyc", "london"}

    transfer = global_cities.list_cities(model_status="TRANSFER")
    # 522 WorldMove rows minus London, which collides by (country_code, name)
    # with the already-registered "london" city and is skipped at build time.
    assert len(transfer) == 521
