"""Tests for models/cross_city_estimation/calibration_eval.py -- the
leave-one-city-out transfer calibration experiment.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from models.cross_city_estimation.calibration_eval import (
    NYC_DB,
    LONDON_DB,
    compute_metrics,
    run_direction,
    run_all,
)

requires_warehouses = pytest.mark.skipif(
    not (NYC_DB.exists() and LONDON_DB.exists()), reason="both warehouses required"
)


def test_zero_circularity_fitted_rate_depends_only_on_train_city():
    # eval_df's demand is wildly different from train_df's -- if the fitted
    # rate were contaminated by eval data, it would drift toward eval's
    # scale. It must not: it's a pure function of train_df/train_pop.
    train_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "total_demand": [1000.0] * 5})
    eval_df_a = pd.DataFrame({"date": pd.date_range("2024-02-01", periods=5), "total_demand": [1.0] * 5})
    eval_df_b = pd.DataFrame({"date": pd.date_range("2024-02-01", periods=5), "total_demand": [999_999.0] * 5})

    result_a = run_direction("train", "eval", train_df, eval_df_a, 100.0, 200.0)
    result_b = run_direction("train", "eval", train_df, eval_df_b, 100.0, 200.0)

    assert result_a["fitted_rate_per_capita"] == result_b["fitted_rate_per_capita"] == pytest.approx(10.0)


def test_compute_metrics_excludes_zero_actuals_from_mape_only():
    import numpy as np

    actual = np.array([0.0, 10.0, 20.0])
    predicted = np.array([5.0, 10.0, 22.0])
    m = compute_metrics(actual, predicted)
    # MAE/RMSE/WAPE must still account for the zero-actual row's error (5.0)
    assert m["mae"] == pytest.approx((5.0 + 0.0 + 2.0) / 3)
    # MAPE only over the two nonzero rows: |0/10| and |2/20|
    assert m["mape_pct"] == pytest.approx(((0 / 10) + (2 / 20)) / 2 * 100)


@requires_warehouses
def test_run_all_produces_no_nulls_and_real_periods():
    result = run_all()
    assert result["confidence_basis"] == "limited_two_city_leave_one_out"
    for exp in result["experiments"].values():
        assert exp["train_period"][0] != exp["train_period"][1]  # real range, not a single-day fluke
        assert exp["evaluation_period"][0] != exp["evaluation_period"][1]
        for baseline in exp["baselines"].values():
            for key in ("mae", "rmse", "wape_pct"):
                assert baseline[key] is not None


if __name__ == "__main__":
    test_zero_circularity_fitted_rate_depends_only_on_train_city()
    test_compute_metrics_excludes_zero_actuals_from_mape_only()
    print("test_cross_city_calibration_eval self-check OK")
