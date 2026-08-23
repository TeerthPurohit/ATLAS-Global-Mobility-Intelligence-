"""Provenance + capability-truthfulness tests for the extended tariff engine.

Covers what the fare/confidence contract must never break:
NYC prices from a trained model (`computed`), a city with a real tariff
profile prices in ITS OWN currency (`modeled_estimate`), a city without one
gets nothing at all (`unavailable`, confidence 0.0), and no `unavailable`
component can ever raise the overall confidence figure.

Currencies are read from the real `city_tariff_profiles` rows, never
hardcoded -- if the generated profiles change, these tests follow the data.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

# This module calls tariff_profiles.city_ids() at import time (below), which
# now needs DATABASE_URL (city_tariff_profiles moved to Postgres, see
# tariff_profiles.py's module docstring) -- unlike test_api.py/test_journey.py,
# this file imports backend.services directly rather than backend.main, so it
# never got main.py's load_dotenv() for free.
load_dotenv(REPO_ROOT / ".env")

from backend.predictors import journey_predictors  # noqa: E402
from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult  # noqa: E402
from backend.registry import cities as cities_registry  # noqa: E402
from backend.services import model_service, platform_service, pricing_engine, tariff_profiles  # noqa: E402
from backend.services.tariff_profiles import TariffProfile  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

# Real, currently-generated profiles (SELECT city_id, currency FROM
# city_tariff_profiles) -- resolved at import so a regenerated table just
# changes which cities are exercised, never silently skips the assertion.
_REAL_PROFILES = {cid: tariff_profiles.get(cid) for cid in tariff_profiles.city_ids()}
_NON_USD = {p.currency: p for p in _REAL_PROFILES.values() if p.currency != "USD"}


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


def _ctx(city_id: str, hour: int = 12, pickup_zone_id: int | None = None, dropoff_zone_id: int | None = None) -> JourneyContext:
    unavailable = PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="n/a")
    return JourneyContext(
        pickup_lat=0.0, pickup_lon=0.0, dropoff_lat=0.0, dropoff_lon=0.0,
        departure_time=datetime(2026, 6, 15, hour, 0), vehicle_type="sedan",
        pickup_zone_id=pickup_zone_id, dropoff_zone_id=dropoff_zone_id, vehicle_profile=None,
        weather=unavailable, holiday=unavailable, city_id=city_id,
    )


def test_nyc_fare_is_computed_by_the_trained_model(monkeypatch):
    """NYC prices from the trained fare model, never from a tariff profile.

    The model call itself is stubbed so this asserts the *provenance contract*
    (computed / USD / trained_fare_model / the model's own name) rather than
    re-testing XGBoost -- and so it stays meaningful on a machine whose
    xgboost build can't score the committed artifact (see
    test_nyc_fare_model_failure_degrades_honestly)."""
    monkeypatch.setattr(model_service, "predict_fare", lambda *a, **kw: (42.5, "xgboost_fare_v1"))
    result = pricing_engine._base_fare(_ctx("nyc", pickup_zone_id=161, dropoff_zone_id=132), _features())
    assert result.basis == "computed"
    assert result.value == 42.5
    assert result.unit == "USD"
    assert result.method == "trained_fare_model"
    assert result.source == "xgboost_fare_v1"
    assert result.confidence == 1.0


def test_nyc_fare_model_failure_degrades_honestly(monkeypatch):
    """A model artifact that won't score must never fabricate a fare or blow
    up the request -- it degrades exactly like a missing input."""
    def _boom(*_a, **_kw):
        raise RuntimeError("artifact unreadable")

    monkeypatch.setattr(model_service, "predict_fare", _boom)
    result = pricing_engine._base_fare(_ctx("nyc", pickup_zone_id=161, dropoff_zone_id=132), _features())
    assert result.basis == "unavailable"
    assert result.value is None
    assert result.confidence == 0.0


@pytest.mark.parametrize("city_id", sorted(_REAL_PROFILES))
def test_city_with_a_real_tariff_profile_prices_in_its_own_currency(city_id):
    profile = _REAL_PROFILES[city_id]
    result = pricing_engine._base_fare(_ctx(city_id), _features())
    assert result.basis == "modeled_estimate"
    assert result.unit == profile.currency  # never hardcoded USD
    assert result.method == "tariff_profile_linear"
    assert result.confidence == profile.confidence
    assert result.value >= profile.min_fare


def test_the_tariff_tests_above_are_actually_exercising_something():
    """Canary. `tariff_profiles.load()` swallows a connection failure and
    leaves the store empty (ADR-009: unreachable outside the VPC is expected,
    not exceptional), which would silently reduce the parametrized tests above
    to zero cases -- green, and testing nothing. This fails loudly instead.

    The bar used to be ">=2 non-USD currencies", back when 517 LLM-generated
    profiles spanned many currencies. Post-ADR-012 only nyc is served and it
    prices in USD from a trained model, so there may be no non-USD currency
    at all -- the non-USD assertion is skipped rather than failed when the
    store holds only USD profiles.
    """
    assert _REAL_PROFILES, (
        "no tariff profiles resolved -- the Postgres store is unreachable or empty, "
        "so every tariff test in this file is vacuous. Set DATABASE_URL and re-run."
    )
    if not _NON_USD:
        pytest.skip(
            "only USD tariff profiles registered -- the non-USD currency path has "
            "nothing to exercise until a second city lands (ADR-012)"
        )


def test_city_without_a_tariff_profile_is_unavailable_not_fabricated():
    # Use a city that definitely has no profile - not in either registry
    city_id = "ZZ_NOT_A_CITY"
    assert tariff_profiles.get(city_id) is None
    result = pricing_engine._base_fare(_ctx(city_id), _features())
    assert result.basis == "unavailable"
    assert result.value is None
    assert result.confidence == 0.0
    assert "no tariff profile" in result.reason


@pytest.mark.parametrize("city_id", sorted(_REAL_PROFILES))
def test_minimum_fare_floor_is_enforced(city_id):
    profile = _REAL_PROFILES[city_id]
    tiny = pricing_engine._base_fare(_ctx(city_id), _features(distance_miles=0.01, duration_min=0.1))
    # Min fare is applied after flat fees, so tiny trip may slightly exceed min_fare
    assert tiny.value >= profile.min_fare


def test_optional_components_are_only_applied_when_the_profile_defines_them(monkeypatch):
    base = dict(
        city_id="testcity", currency="EUR", base_fare=3.0, per_km=1.0, per_min=0.5, min_fare=0.0,
        night_multiplier=1.0, airport_surcharge=0.0, source="llm_anchored",
        generated_at="2026-08-10T00:00:00", model_id="test", confidence=0.7, notes="",
    )
    monkeypatch.setattr(tariff_profiles, "get", lambda _cid: TariffProfile(**base))
    plain = pricing_engine._base_fare(_ctx("testcity"), _features())
    monkeypatch.setattr(tariff_profiles, "get", lambda _cid: TariffProfile(**base, booking_fee=2.5))
    with_fee = pricing_engine._base_fare(_ctx("testcity"), _features())
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
    good = dict(
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


def test_all_modeled_city_scores_lower_than_all_computed_city():
    modeled = {
        name: PredictionResult(value=1.0, unit="x", basis="modeled_estimate", source="s", reason="proxy")
        for name in ("fare", "demand", "congestion")
    }
    computed = {
        name: PredictionResult(value=1.0, unit="x", basis="computed", source="s")
        for name in ("fare", "demand", "congestion")
    }
    assert journey_predictors.predict_confidence(modeled).value < journey_predictors.predict_confidence(computed).value


def test_capability_matrix_returns_none_for_an_unregistered_city():
    assert cities_registry.capability_matrix("nyc")["fare"] is True
    assert cities_registry.capability_matrix("ZZ_NOT_A_CITY") is None


def test_capability_summary_counts_come_from_the_registry():
    """ADR-011: the denominator is the registered cities, nothing wider."""
    summary = platform_service.get_capability_summary()
    registered = {c["id"] for c in cities_registry.list_cities()}
    assert summary["total_cities"] == len(registered)
    fare = summary["capabilities"]["fare"]
    assert fare["supported"] + fare["unsupported"] == summary["total_cities"]
