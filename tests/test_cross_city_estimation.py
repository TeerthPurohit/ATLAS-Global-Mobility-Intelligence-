"""Tests for models/cross_city_estimation/estimate.py (SPEC-015 FR-5).

With only two real calibration points (NYC, London) there is no ground
truth to check a third city's estimate *against* -- these tests deliberately
check "doesn't crash, returns a plausible-range, honestly-labeled result"
rather than numerical accuracy, per the task instructions. A precision test
would just be re-asserting the same arithmetic the module already does.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.cross_city_estimation.estimate import (
    LONDON_DAILY_RATE_PER_CAPITA,
    NYC_DAILY_RATE_PER_CAPITA,
    estimate_demand_per_capita,
)


def test_reference_rates_are_real_and_distinct():
    # Both computed from real total_trips/date-range/population inputs cited
    # in the module docstring -- neither should be zero or negative, and
    # they shouldn't coincidentally match (different mobility products).
    assert NYC_DAILY_RATE_PER_CAPITA > 0
    assert LONDON_DAILY_RATE_PER_CAPITA > 0
    assert NYC_DAILY_RATE_PER_CAPITA != LONDON_DAILY_RATE_PER_CAPITA


def test_third_city_population_returns_plausible_labeled_estimate():
    # A third city (e.g. Chicago-scale population) with no real trip data of
    # its own -- the point of this function.
    value, reason = estimate_demand_per_capita(2_700_000)
    low_bound = 2_700_000 * min(NYC_DAILY_RATE_PER_CAPITA, LONDON_DAILY_RATE_PER_CAPITA)
    high_bound = 2_700_000 * max(NYC_DAILY_RATE_PER_CAPITA, LONDON_DAILY_RATE_PER_CAPITA)
    assert low_bound <= value <= high_bound
    # Never a "computed" claim -- the reason string must self-disclose the
    # weak N=2 basis every time, not just in the docstring.
    assert "N=2" in reason
    assert "never a validated model" in reason


def test_density_argument_nudges_but_does_not_explode_the_estimate():
    base_value, _ = estimate_demand_per_capita(1_000_000)
    dense_value, dense_reason = estimate_demand_per_capita(1_000_000, density=20000)
    sparse_value, sparse_reason = estimate_demand_per_capita(1_000_000, density=500)
    assert dense_value > base_value > sparse_value
    assert "density-adjusted" in dense_reason
    # clamped multiplier (0.5x-2x) -- density can't blow the estimate up
    # arbitrarily with only 2 real reference points backing it.
    assert dense_value <= base_value * 2.01
    assert sparse_value >= base_value * 0.49


def test_invalid_population_rejected():
    with pytest.raises(ValueError):
        estimate_demand_per_capita(0)
    with pytest.raises(ValueError):
        estimate_demand_per_capita(-100)


if __name__ == "__main__":
    test_reference_rates_are_real_and_distinct()
    test_third_city_population_returns_plausible_labeled_estimate()
    test_density_argument_nudges_but_does_not_explode_the_estimate()
    test_invalid_population_rejected()
    print("test_cross_city_estimation self-check OK")
