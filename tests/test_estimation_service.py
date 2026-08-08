"""Tests for backend/services/estimation_service.py (SPEC-015 FR-5 wrapper).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.services.estimation_service import estimate_city_demand  # noqa: E402


def test_estimate_city_demand_returns_modeled_estimate():
    res = estimate_city_demand("chicago", population=2_700_000, density=4500)
    assert res.basis == "modeled_estimate"
    assert res.unit == "trips/day"
    assert res.value > 0
    assert res.reason is not None
    assert "N=2" in res.reason
    assert "never a validated model" in res.reason


def test_estimate_city_demand_invalid_population():
    res = estimate_city_demand("atlantis", population=0)
    assert res.basis == "unavailable"
    assert res.value is None
    assert "positive" in res.reason


if __name__ == "__main__":
    test_estimate_city_demand_returns_modeled_estimate()
    test_estimate_city_demand_invalid_population()
    print("test_estimation_service OK")
