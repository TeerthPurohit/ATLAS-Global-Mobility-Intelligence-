"""Chronological train/validation/test split (ADR-003).

Never random-split time-ordered rows here — a random split lets lag/EWMA
features leak a smoothed echo of the test target into training. Split by
row count after sorting on the timestamp column instead.

Promoted here (Phase 2 dedup, IMPLEMENTATION_AUDIT.md section 9/10) from
`models/data_prep/train_test_split.py`, which now just re-exports these
names for backward compatibility. `models/fare_prediction/train_fare_xgb.py`
used to carry its own byte-for-byte-identical copy of `_latest_month_start()`
plus an inline reimplementation of `split_demand_blocks()` — it now calls
`split_demand_blocks()` directly instead.

`split_demand_blocks()` is the gap-aware entry point: a plain row-count
fraction split across concatenated date-gapped blocks would land the test
cutoff mid-block, mixing early "train" rows with late "test" rows from the
same month. Every model in this repo instead holds the most recent calendar
month out as test in full, and takes the most recent 15% of everything
before it (by timestamp) as validation — computed from the data's own max
date, not hardcoded, so newly-arrived months never silently get dumped
into an oversized "test" split.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _latest_month_start(df: pd.DataFrame, ts_col: str) -> pd.Timestamp:
    max_ts = pd.Timestamp(df[ts_col].max())
    return pd.Timestamp(year=max_ts.year, month=max_ts.month, day=1)


def split_demand_blocks(df: pd.DataFrame, ts_col: str = "ts") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """train/val = every month before the latest one (chronological 85/15),
    test = the latest calendar month in full."""
    test_block_start = _latest_month_start(df, ts_col)
    train_val = df[df[ts_col] < test_block_start]
    test = df[df[ts_col] >= test_block_start]
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
    assert test2["ts"].min() >= _latest_month_start(blocky, "ts")
    print(f"demand split: train={len(train2)} val={len(val2)} test={len(test2)}")


if __name__ == "__main__":
    demo()
