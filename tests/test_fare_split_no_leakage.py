"""Leakage-guard test for the fare-prediction chronological split (SPEC-007,
ADR-003): train must fully precede val, val must fully precede test.
"""

import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from fare_prediction.train_fare_xgb import DEFAULT_DB_PATH, split_data  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="warehouse not built")


def test_fare_chronological_split_no_leakage():
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        df = con.execute("select pickup_at from int_trips_enriched").fetchdf()
    finally:
        con.close()

    # split_data() itself computes the test-block cutoff from the data's own
    # max date (models/fare_prediction/train_fare_xgb.py's _latest_month_start)
    # -- exercising the real function under test, not a duplicated cutoff.
    train, val, test = split_data(df)

    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["pickup_at"].max() < val["pickup_at"].min()
    assert val["pickup_at"].max() < test["pickup_at"].min()
