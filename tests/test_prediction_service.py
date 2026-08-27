"""Correctness tests for prediction_service.py (SPEC-013 FR-7):
capability-gated prediction for a supported metric matches direct
model_service output; an unsupported metric returns CAPABILITY_UNAVAILABLE
and a missing registry row raises CITY_NOT_FOUND, never a fabricated number.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.errors import DomainError  # noqa: E402, I001
from backend.registry import cities as cities_registry  # noqa: E402
from backend.registry import models as models_registry  # noqa: E402
from backend.schemas import CapabilityUnavailable, ErrorCode, PredictionEnvelope  # noqa: E402
from backend.services import model_service  # noqa: E402
from backend.services import prediction_service  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module", autouse=True)
def _load_registries():
    model_service.load()
    models_registry.load()
    cities_registry.load()


def test_predict_demand_matches_model_service_directly():
    expected_value, expected_model = model_service.predict_demand(132, 8, 1)
    envelope = prediction_service.predict_demand(132, 8, 1)
    assert isinstance(envelope, PredictionEnvelope)
    assert envelope.prediction == expected_value
    assert envelope.model == expected_model
    assert envelope.city_id == "nyc"
    assert envelope.area_id == 132


def test_predict_fare_matches_model_service_directly():
    expected_value, expected_model = model_service.predict_fare(132, 230, 8)
    envelope = prediction_service.predict_fare(132, 230, 8)
    assert isinstance(envelope, PredictionEnvelope)
    assert envelope.prediction == expected_value
    assert envelope.model == expected_model
    assert envelope.dropoff_area_id == 230


def test_missing_registry_row_raises_city_not_found(monkeypatch):
    """No caller passes a city any more (ADR-013), so the only way this guard
    fires is a `cities` seed with no row -- a deployment fault, surfaced
    rather than served as a fabricated profile."""
    monkeypatch.setattr(cities_registry, "get_city_profile", lambda: None)
    with pytest.raises(DomainError) as exc_info:
        prediction_service.predict_demand(132, 8, 1)
    assert exc_info.value.code == ErrorCode.CITY_NOT_FOUND


def test_predict_demand_unknown_area_returns_prediction_failed():
    with pytest.raises(DomainError) as exc_info:
        prediction_service.predict_demand(999999, 8, 1)
    assert exc_info.value.code == ErrorCode.PREDICTION_FAILED


def test_forecast_unsupported_metric_returns_capability_unavailable_not_fake_data():
    result = prediction_service.forecast("weather")
    assert isinstance(result, CapabilityUnavailable)
    assert result.available is False
    assert result.capability == "weather"


def test_forecast_invalid_hours_raises_invalid_time_range():
    with pytest.raises(DomainError) as exc_info:
        prediction_service.forecast("demand", hours=999)
    assert exc_info.value.code == ErrorCode.INVALID_TIME_RANGE
