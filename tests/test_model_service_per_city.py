"""Regression test for the per-city model_service.py fix: London's demand
prediction must use London's own trained model (or its EWMA fallback),
never silently fall back to serving NYC's model under London's name.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.services import model_service  # noqa: E402

NYC_WAREHOUSE = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
LONDON_WAREHOUSE = REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb"

pytestmark = pytest.mark.skipif(
    not (NYC_WAREHOUSE.exists() and LONDON_WAREHOUSE.exists()), reason="warehouses not built"
)


@pytest.fixture(scope="module", autouse=True)
def _load():
    model_service.load()


def test_london_demand_prediction_uses_london_model():
    momentum = model_service._zone_momentum.get("london", {})
    assert momentum, "expected London demand history to be loaded"
    area_id = next(iter(momentum))
    value, model_name = model_service.predict_demand(area_id, 8, 1, city_id="london")
    assert model_name in ("xgboost_london_demand_v1", "ewma_fallback_v1")
    assert value >= 0


def test_nyc_call_sites_default_correctly():
    value, model_name = model_service.predict_demand(132, 8, 1)  # legacy call shape, no city_id
    assert model_name in ("xgboost_demand_v1", "ewma_fallback_v1")
    assert value >= 0


def test_unregistered_city_raises_keyerror():
    with pytest.raises(KeyError):
        model_service.predict_demand(1, 8, 1, city_id="mumbai")


def demo() -> None:
    model_service.load()
    test_london_demand_prediction_uses_london_model()
    test_nyc_call_sites_default_correctly()
    test_unregistered_city_raises_keyerror()
    print("test_model_service_per_city demo OK")


if __name__ == "__main__":
    demo()
