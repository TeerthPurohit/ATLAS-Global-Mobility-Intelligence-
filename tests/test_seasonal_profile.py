"""Regression test for the "stale numbers" fix (docs/superpowers/specs
recovery plan): predict_demand() must actually respond to the requested
hour/day_of_week/month instead of reusing one frozen last-known-row
snapshot (2024-06-30) for every query regardless of what was asked.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.services import model_service  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")

ZONE_ID = 132  # JFK Airport -- high volume, has history across every hour/day slot


@pytest.fixture(scope="module", autouse=True)
def _load():
    model_service.load()


def test_demand_varies_by_hour_and_day_of_week():
    monday_morning, _ = model_service.predict_demand(ZONE_ID, 8, 0)
    sunday_night, _ = model_service.predict_demand(ZONE_ID, 3, 6)
    assert monday_morning != sunday_night


def test_demand_varies_by_month_when_measured():
    # Jan is real (in the warehouse's Jan/Mar/Jun 2024 coverage); the model's
    # raw hour/day prediction gets scaled by a real month-of-year multiplier.
    unscaled, _ = model_service.predict_demand(ZONE_ID, 8, 0)
    january, _ = model_service.predict_demand(ZONE_ID, 8, 0, month=1)
    assert january != unscaled


def test_data_vintage_reports_real_range_not_a_single_date():
    vintage = model_service.data_vintage()
    assert vintage is not None
    assert " to " in vintage


def test_hourly_shape_fractions_sum_to_one_per_day_of_week():
    for dow in range(7):
        total = sum(model_service.hourly_shape_fraction(h, dow) or 0.0 for h in range(24))
        assert abs(total - 1.0) < 1e-6


def demo() -> None:
    model_service.load()
    test_demand_varies_by_hour_and_day_of_week()
    test_demand_varies_by_month_when_measured()
    test_data_vintage_reports_real_range_not_a_single_date()
    test_hourly_shape_fractions_sum_to_one_per_day_of_week()
    print("test_seasonal_profile demo OK")


if __name__ == "__main__":
    demo()
