"""Chronological train/validation/test split (ADR-003).

Never random-split time-ordered rows here — a random split lets lag/EWMA
features leak a smoothed echo of the test target into training. Split by
row count after sorting on the timestamp column instead.

This is a plain row-count fraction splitter for a *continuous* series. If
the underlying data has gaps (e.g. missing months), pre-filter to the
block(s) you want before calling this — see
models/fare_prediction/train_fare_xgb.py for a worked example that holds an
entire month block out as test rather than trusting a fraction cutoff to
land in the right place.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Warehouse only has Jan/Mar/Jun 2024 (Feb/Apr/May missing, per EDA). A plain
# row-count-fraction split across the concatenated blocks would land the test
# cutoff partway into June (Jan+Mar is already ~2/3 of all rows), mixing
# early-June "train" rows with late-June "test" rows from the same block --
# same reasoning as models/fare_prediction/train_fare_xgb.py. So every model
# in this ladder holds out June whole as test, and takes the most recent 15%
# of Jan+Mar (by timestamp) as validation.
DEMAND_TEST_BLOCK_START = "2024-06-01"


def split_demand_blocks(df: pd.DataFrame, ts_col: str = "ts") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """train/val = Jan+Mar (chronological 85/15), test = June in full."""
    train_val = df[df[ts_col] < DEMAND_TEST_BLOCK_START]
    test = df[df[ts_col] >= DEMAND_TEST_BLOCK_START]
    train, val = chronological_split(train_val, ts_col, (0.85, 0.15))
    return train, val, test


def chronological_split(
    df: pd.DataFrame, ts_col: str, fracs: tuple[float, ...] = (0.7, 0.15, 0.15)
) -> list[pd.DataFrame]:
    """Sort `df` by `ts_col` and slice into len(fracs) chunks, in the given
    proportions. Cutoffs land on *unique timestamp* boundaries (not raw row
    count) so that rows sharing an identical timestamp -- e.g. every zone's
    row for the same hour, as in the demand feature table -- always land in
    the same split. Splitting by raw row position would otherwise cut a
    timestamp group in half and put the same hour in both train and val."""
    assert abs(sum(fracs) - 1.0) < 1e-6, "fracs must sum to 1.0"
    sorted_df = df.sort_values(ts_col).reset_index(drop=True)
    unique_ts = np.sort(sorted_df[ts_col].unique())
    n = len(unique_ts)
    splits = []
    start = 0
    cum = 0.0
    for i, frac in enumerate(fracs):
        cum += frac
        end = n if i == len(fracs) - 1 else round(n * cum)
        ts_chunk = unique_ts[start:end]
        splits.append(sorted_df[sorted_df[ts_col].isin(ts_chunk)])
        start = end
    return splits


def demo() -> None:
    df = pd.DataFrame({"ts": pd.date_range("2024-01-01", periods=100, freq="h")})
    train, val, test = chronological_split(df, "ts", (0.7, 0.15, 0.15))
    assert len(train) + len(val) + len(test) == len(df)
    assert train["ts"].max() < val["ts"].min()
    assert val["ts"].max() < test["ts"].min()
    print(f"train={len(train)} val={len(val)} test={len(test)}")

    blocky = pd.concat(
        [
            pd.DataFrame({"ts": pd.date_range("2024-01-01", periods=100, freq="h")}),
            pd.DataFrame({"ts": pd.date_range("2024-06-01", periods=50, freq="h")}),
        ]
    )
    train2, val2, test2 = split_demand_blocks(blocky)
    assert train2["ts"].max() < val2["ts"].min() < test2["ts"].min()
    assert test2["ts"].min() >= pd.Timestamp(DEMAND_TEST_BLOCK_START)
    print(f"demand split: train={len(train2)} val={len(val2)} test={len(test2)}")


if __name__ == "__main__":
    demo()
