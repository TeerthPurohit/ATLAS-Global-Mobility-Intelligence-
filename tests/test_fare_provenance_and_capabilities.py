"""Provenance + capability-truthfulness tests for the extended tariff engine.

Covers what the fare/confidence contract must never break: the served city
prices from a trained model (`computed`); the tariff formula that backs
`prediction_service.predict_fare()`'s area-pair path prices in the profile's
own currency (`modeled_estimate`); no profile at all yields nothing rather
than a fabricated number (`unavailable`, confidence 0.0); and no
`unavailable` component can ever raise the overall confidence figure.

Currency is read from the real `city_tariff_profiles` row, never hardcoded --
if the generated profile changes, these tests follow the data.

Since ADR-013 the journey path (`_base_fare`) always uses the trained model,
so the tariff assertions below target `_base_fare_tariff` directly -- the
same function `estimate_tariff_base_fare()` calls, not a test-only branch.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

# This module reads tariff_profiles at import time (below), which needs
# DATABASE_URL (city_tariff_profiles moved to Postgres, see
# tariff_profiles.py's module docstring) -- unlike test_api.py/test_journey.py,
# this file imports backend.services directly rather than backend.main, so it
# never got main.py's load_dotenv() for free.
load_dotenv(REPO_ROOT / ".env")

from backend.predictors import journey_predictors  # noqa: E402, I001
from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult  # noqa: E402
from backend.registry import cities as cities_registry  # noqa: E402
from backend.services import model_service, platform_service, pricing_engine, tariff_profiles  # noqa: E402
from backend.services.tariff_profiles import TariffProfile  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

# The real, currently-generated profile (SELECT * FROM city_tariff_profiles
# WHERE city_id = 'nyc') -- resolved at import so a regenerated table changes
# what these tests assert against, never silently skips the assertion.
_REAL_PROFILE = tariff_profiles.get()


def _features(distance_miles: float | None = 5.0, duration_min: float = 15.0) -> JourneyFeatures:
    unavailable = PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="n/a")
    return JourneyFeatures(
        distance_miles=PredictionResult(value=distance_miles, unit="miles", basis="computed", source="osrm")
        if distance_miles is not None else unavailable,
        duration_min=PredictionResult(value=duration_min, unit="minutes", basis="computed", source="osrm"),
        weather_score=unavailable,
        holiday_score=unavailable,
        historical_traffic_score=unavailable,
        vehicle_profile=None,
    )


def _ctx(hour: int = 12, pickup_zone_id: int | None = None, dropoff_zone_id: int | None = None) -> JourneyContext:
    unavailable = PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="n/a")
    return JourneyContext(
        pickup_lat=0.0, pickup_lon=0.0, dropoff_lat=0.0, dropoff_lon=0.0,
        departure_time=datetime(2026, 6, 15, hour, 0), vehicle_type="sedan",  # noqa: DTZ001
        pickup_zone_id=pickup_zone_id, dropoff_zone_id=dropoff_zone_id, vehicle_profile=None,
        weather=unavailable, holiday=unavailable,
    )


def test_fare_is_computed_by_the_trained_model(monkeypatch):
    """The journey path prices from the trained fare model, never from a
    tariff profile.

    The model call itself is stubbed so this asserts the *provenance contract*
    (computed / USD / trained_fare_model / the model's own name) rather than
    re-testing XGBoost -- and so it stays meaningful on a machine whose
    xgboost build can't score the committed artifact (see
    test_fare_model_failure_degrades_honestly)."""
    monkeypatch.setattr(model_service, "predict_fare", lambda *a, **kw: (42.5, "xgboost_fare_v1"))
    result = pricing_engine._base_fare(_ctx(pickup_zone_id=161, dropoff_zone_id=132), _features())
    assert result.basis == "computed"
    assert result.value == 42.5
    assert result.unit == "USD"
    assert result.method == "trained_fare_model"
    assert result.source == "xgboost_fare_v1"
    assert result.confidence == 1.0


def test_fare_model_failure_degrades_honestly(monkeypatch):
    """A model artifact that won't score must never fabricate a fare or blow
    up the request -- it degrades exactly like a missing input."""
    def _boom(*_a, **_kw):
        raise RuntimeError("artifact unreadable")

    monkeypatch.setattr(model_service, "predict_fare", _boom)
    result = pricing_engine._base_fare(_ctx(pickup_zone_id=161, dropoff_zone_id=132), _features())
    assert result.basis == "unavailable"
    assert result.value is None
    assert result.confidence == 0.0


def test_the_tariff_tests_below_are_actually_exercising_something():
    """Canary. `tariff_profiles.load()` swallows a connection failure and
    leaves the store empty (ADR-009: unreachable outside the VPC is expected,
    not exceptional), which would leave every tariff assertion below asserting
    against None. This fails loudly instead."""
    assert _REAL_PROFILE is not None, (
        "no tariff profile resolved -- the Postgres store is unreachable or empty, "
        "so every tariff test in this file is vacuous. Set DATABASE_URL and re-run."
    )


@pytest.mark.skipif(_REAL_PROFILE is None, reason="no tariff profile in the store")
def test_the_tariff_path_prices_in_the_profiles_own_currency():
    result = pricing_engine._base_fare_tariff(_ctx(), _features())
    assert result.basis == "modeled_estimate"
    assert result.unit == _REAL_PROFILE.currency  # never hardcoded USD
    assert result.method == "tariff_profile_linear"
    assert result.confidence == _REAL_PROFILE.confidence
    assert result.value >= _REAL_PROFILE.min_fare


def test_no_tariff_profile_is_unavailable_not_fabricated(monkeypatch):
    monkeypatch.setattr(tariff_profiles, "get", lambda: None)
    result = pricing_engine._base_fare_tariff(_ctx(), _features())
    assert result.basis == "unavailable"
    assert result.value is None
    assert result.confidence == 0.0
    assert "no tariff profile" in result.reason


@pytest.mark.skipif(_REAL_PROFILE is None, reason="no tariff profile in the store")
def test_minimum_fare_floor_is_enforced():
    tiny = pricing_engine._base_fare_tariff(_ctx(), _features(distance_miles=0.01, duration_min=0.1))
    # Min fare is applied after flat fees, so a tiny trip may slightly exceed min_fare
    assert tiny.value >= _REAL_PROFILE.min_fare


def test_optional_components_are_only_applied_when_the_profile_defines_them(monkeypatch):
    base = dict(  # noqa: C408
        city_id="testcity", currency="EUR", base_fare=3.0, per_km=1.0, per_min=0.5, min_fare=0.0,
        night_multiplier=1.0, airport_surcharge=0.0, source="llm_anchored",
        generated_at="2026-08-10T00:00:00", model_id="test", confidence=0.7, notes="",
    )
    monkeypatch.setattr(tariff_profiles, "get", lambda: TariffProfile(**base))
    plain = pricing_engine._base_fare_tariff(_ctx(), _features())
    monkeypatch.setattr(tariff_profiles, "get", lambda: TariffProfile(**base, booking_fee=2.5))
    with_fee = pricing_engine._base_fare_tariff(_ctx(), _features())
    assert with_fee.value == pytest.approx(plain.value + 2.5)
    assert "booking_fee" not in plain.reason
    assert "booking_fee" in with_fee.reason


@pytest.mark.parametrize(
    "bad",
    [
        {"base_fare": -1.0},
        {"min_fare": -5.0},
        {"per_km": -0.1},
        {"currency": "rupees"},
        {"effective_from": "not-a-date"},
        {"source_type": "vibes"},
    ],
)
def test_malformed_tariff_profiles_are_rejected_at_construction(bad):
    good = dict(  # noqa: C408
        city_id="testcity", currency="EUR", base_fare=3.0, per_km=1.0, per_min=0.5, min_fare=1.0,
        night_multiplier=1.0, airport_surcharge=0.0, source="llm_anchored",
        generated_at="2026-08-10T00:00:00", model_id="test", confidence=0.7, notes="",
    )
    with pytest.raises(ValueError):
        TariffProfile(**{**good, **bad})


def test_unavailable_component_cannot_increase_confidence():
    computed = PredictionResult(value=1.0, unit="x", basis="computed", source="s")
    unavailable = PredictionResult(value=None, unit=None, basis="unavailable", source="s", reason="n/a")
    assert unavailable.confidence == 0.0
    without = journey_predictors.predict_confidence({"a": computed})
    with_gap = journey_predictors.predict_confidence({"a": computed, "b": unavailable})
    assert with_gap.value < without.value


def test_all_modeled_scores_lower_than_all_computed():
    modeled = {
        name: PredictionResult(value=1.0, unit="x", basis="modeled_estimate", source="s", reason="proxy")
        for name in ("fare", "demand", "congestion")
    }
    computed = {
        name: PredictionResult(value=1.0, unit="x", basis="computed", source="s")
        for name in ("fare", "demand", "congestion")
    }
    assert journey_predictors.predict_confidence(modeled).value < journey_predictors.predict_confidence(computed).value


def test_capability_matrix_reflects_what_is_wired():
    assert cities_registry.capability_matrix()["fare"] is True


def test_capability_matrix_is_none_without_a_registered_city(monkeypatch):
    """The only way the matrix is None now is a missing `cities` row -- a
    broken seed, which callers surface rather than paper over."""
    monkeypatch.setattr(cities_registry, "get_city", lambda: None)
    assert cities_registry.capability_matrix() is None


def test_capability_summary_counts_come_from_the_registry():
    """ADR-011/013: the denominator is the registered city, nothing wider."""
    summary = platform_service.get_capability_summary()
    assert summary["total_cities"] == (1 if cities_registry.get_city() else 0)
    fare = summary["capabilities"]["fare"]
    assert fare["supported"] + fare["unsupported"] == summary["total_cities"]
