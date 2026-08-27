"""Phase 2 dedup proof: `train_fare_xgb.split_data()` (now delegating to
the shared `split_demand_blocks()`) produces byte-identical output to the
old inline logic it used to carry, and `train_test_split.py`'s
backward-compatible re-export resolves to the same functions as the new
`chronological_split.py` module.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from data_prep.chronological_split import chronological_split, split_demand_blocks  # noqa: E402, I001
from data_prep import train_test_split as legacy_module  # noqa: E402
from fare_prediction.train_fare_xgb import split_data  # noqa: E402


def _old_split_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The exact logic train_fare_xgb.split_data() used to inline, before
    Phase 2 dedup -- kept here only to prove equivalence, not reused."""
    max_ts = pd.Timestamp(df["pickup_at"].max())
    test_block_start = pd.Timestamp(year=max_ts.year, month=max_ts.month, day=1)
    train_val = df[df["pickup_at"] < test_block_start]
    test = df[df["pickup_at"] >= test_block_start]
    train, val = chronological_split(train_val, "pickup_at", (0.85, 0.15))
    return train, val, test


def _synthetic_gapped_df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    blocks = [
        pd.date_range("2024-01-01", periods=500, freq="h"),
        pd.date_range("2024-03-01", periods=500, freq="h"),
        pd.date_range("2024-06-01", periods=500, freq="h"),
    ]
    ts = pd.DatetimeIndex(np.concatenate(blocks))
    return pd.DataFrame({"pickup_at": ts, "value": rng.random(len(ts))})


def test_new_split_data_matches_old_inline_logic_exactly():
    df = _synthetic_gapped_df()
    train_new, val_new, test_new = split_data(df)
    train_old, val_old, test_old = _old_split_data(df)

    pd.testing.assert_frame_equal(train_new.reset_index(drop=True), train_old.reset_index(drop=True))
    pd.testing.assert_frame_equal(val_new.reset_index(drop=True), val_old.reset_index(drop=True))
    pd.testing.assert_frame_equal(test_new.reset_index(drop=True), test_old.reset_index(drop=True))


def test_legacy_reexport_is_same_function_as_new_module():
    assert legacy_module.split_demand_blocks is split_demand_blocks
    assert legacy_module.chronological_split is chronological_split


if __name__ == "__main__":
    test_new_split_data_matches_old_inline_logic_exactly()
    test_legacy_reexport_is_same_function_as_new_module()
    print("test_chronological_split_dedup self-check OK")
