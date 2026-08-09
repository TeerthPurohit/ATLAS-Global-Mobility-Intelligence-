"""Correctness tests for the tariff-profile fare engine (ADR-011): the LLM
never computes a price, `pricing_engine._base_fare_tariff` does the
arithmetic over a cached `TariffProfile`. Covers the formula's shape, the
min_fare floor, honest degradation with no profile, and that FX (used only
for prompt-anchoring/comparison, never on the price path) can't break a
fare even when unreachable.
"""
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult  # noqa: E402
from backend.services import pricing_engine, tariff_profiles  # noqa: E402
from backend.services.tariff_profiles import TariffProfile  # noqa: E402

_FAKE_PROFILE = TariffProfile(
    city_id="testcity", currency="INR", base_fare=50.0, per_km=12.0, per_min=1.5, min_fare=80.0,
    night_multiplier=1.25, airport_surcharge=0.0, source="llm_anchored",
    generated_at="2026-08-09T00:00:00", model_id="test", confidence=0.7, notes="test fixture",
)


def _features(distance_miles: float | None, duration_min: float = 10.0) -> JourneyFeatures:
    return JourneyFeatures(
        distance_miles=PredictionResult(value=distance_miles, unit="miles", basis="computed", source="osrm") if distance_miles is not None
        else PredictionResult(value=None, unit=None, basis="unavailable", source="osrm", reason="no route"),
        duration_min=PredictionResult(value=duration_min, unit="minutes", basis="computed", source="osrm"),
        weather_score=PredictionResult(value=None, unit=None, basis="unavailable", source="weather", reason="n/a"),
        holiday_score=PredictionResult(value=None, unit=None, basis="unavailable", source="holiday", reason="n/a"),
        historical_traffic_score=PredictionResult(value=None, unit=None, basis="unavailable", source="traffic", reason="n/a"),
        vehicle_profile=None,
    )


def _ctx(city_id: str, hour: int = 12) -> JourneyContext:
    return JourneyContext(
        pickup_lat=0.0, pickup_lon=0.0, dropoff_lat=0.0, dropoff_lon=0.0,
        departure_time=datetime(2026, 8, 9, hour, 0), vehicle_type="mini",
        pickup_zone_id=None, dropoff_zone_id=None, vehicle_profile=None,
        weather=PredictionResult(value=None, unit=None, basis="unavailable", source="weather", reason="n/a"),
        holiday=PredictionResult(value=None, unit=None, basis="unavailable", source="holiday", reason="n/a"),
        city_id=city_id,
    )


def test_fare_monotonic_in_distance(monkeypatch):
    monkeypatch.setattr(tariff_profiles, "get", lambda city_id: _FAKE_PROFILE)
    near = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(1.0))
    far = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(20.0))
    assert far.value > near.value
    assert near.unit == "INR" and far.unit == "INR"
    assert near.basis == "modeled_estimate"


def test_min_fare_floor_holds(monkeypatch):
    monkeypatch.setattr(tariff_profiles, "get", lambda city_id: _FAKE_PROFILE)
    tiny_trip = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(0.01, duration_min=0.1))
    assert tiny_trip.value == _FAKE_PROFILE.min_fare


def test_missing_profile_is_unavailable_not_fabricated(monkeypatch):
    monkeypatch.setattr(tariff_profiles, "get", lambda city_id: None)
    result = pricing_engine._base_fare_tariff(_ctx("nowhere"), _features(5.0))
    assert result.basis == "unavailable"
    assert result.value is None
    assert "no tariff profile" in result.reason


def test_fx_unavailable_does_not_break_local_currency_fare(monkeypatch):
    """FX is never on the fare path -- forcing it to fail must not change
    the result at all."""
    monkeypatch.setattr(tariff_profiles, "get", lambda city_id: _FAKE_PROFILE)
    from backend.adapters import fx_rates

    def _broken(*a, **kw):
        raise RuntimeError("fx unreachable")

    monkeypatch.setattr(fx_rates, "get_rate", _broken)
    result = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(5.0))
    assert result.value is not None
    assert result.unit == "INR"


def demo() -> None:
    class _Patch:
        def __init__(self):
            self._orig = tariff_profiles.get

        def __enter__(self):
            tariff_profiles.get = lambda city_id: _FAKE_PROFILE
            return self

        def __exit__(self, *a):
            tariff_profiles.get = self._orig

    with _Patch():
        near = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(1.0))
        far = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(20.0))
        assert far.value > near.value
        tiny = pricing_engine._base_fare_tariff(_ctx("testcity"), _features(0.01, duration_min=0.1))
        assert tiny.value == _FAKE_PROFILE.min_fare
    print("test_tariff_profiles demo OK")


if __name__ == "__main__":
    demo()
