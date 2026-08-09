"""Phase 6 leakage guard + honesty test for the congestion model
(ADR-003 + standards.md): chronological split must not leak, and
free_flow_source must be honestly labeled 'estimated' in every output row,
never silently defaulted to something implying observed ground truth.
"""
import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from congestion.build_features import DEFAULT_DB_PATH, build_features  # noqa: E402
from data_prep.chronological_split import split_demand_blocks  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def features_df():
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        return build_features(con, sample_rows=20_000)
    finally:
        con.close()


def test_congestion_chronological_split_no_leakage(features_df):
    train, val, test = split_demand_blocks(features_df, "pickup_at")
    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["pickup_at"].max() < val["pickup_at"].min()
    assert val["pickup_at"].max() < test["pickup_at"].min()


def test_free_flow_source_labeled_estimated_not_observed(features_df):
    assert not features_df.empty
    assert (features_df["free_flow_source"] == "estimated").all()
    assert "observed" not in features_df["free_flow_source"].unique().tolist()
