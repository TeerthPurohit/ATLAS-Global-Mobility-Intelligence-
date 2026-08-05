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

from data_prep.train_test_split import chronological_split  # noqa: E402
from fare_prediction.train_fare_xgb import DEFAULT_DB_PATH, TEST_BLOCK_START  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="warehouse not built")


def test_fare_chronological_split_no_leakage():
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        df = con.execute("select pickup_at from int_trips_enriched").fetchdf()
    finally:
        con.close()

    train_val = df[df["pickup_at"] < TEST_BLOCK_START]
    test = df[df["pickup_at"] >= TEST_BLOCK_START]
    train, val = chronological_split(train_val, "pickup_at", (0.85, 0.15))

    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["pickup_at"].max() < val["pickup_at"].min()
    assert val["pickup_at"].max() < test["pickup_at"].min()
