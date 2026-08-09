"""predict.py must degrade gracefully (basis="unavailable" or a documented
fallback), never crash, when a city has no real WorldMove/global_cities
data -- unknown city_id, and a synthetic city row with all-NaN covariates."""

import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from models.global_transfer.predict import ARTIFACT_DIR, NYC_DB, predict  # noqa: E402
from models.global_transfer.build_features import CITY_FEATURE_COLUMNS, apply_scaler  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (NYC_DB.exists() and (ARTIFACT_DIR / "xgb_model.json").exists()),
    reason="warehouse or trained model artifact not present",
)


def test_unknown_city_id_degrades_gracefully():
    con = duckdb.connect(str(NYC_DB), read_only=True)
    try:
        result = predict("NOT_A_REAL_CITY_ID", hour=8, day_of_week=1, con=con)
    finally:
        con.close()
    assert result["value"] is None
    assert result["basis"] == "unavailable"
    assert result["reason"]


def test_apply_scaler_handles_all_nan_row_without_crashing():
    """A city with zero known covariates (no worldmove match, no lat/lon,
    unknown mobility mode) must still scale to a finite (imputed) vector,
    not raise or produce NaN."""
    row = pd.DataFrame([{col: float("nan") for col in CITY_FEATURE_COLUMNS}])
    scaler = {col: {"mean": 1.0, "std": 2.0} for col in CITY_FEATURE_COLUMNS}
    scaled = apply_scaler(row, scaler)
    assert not scaled.isna().any().any()
