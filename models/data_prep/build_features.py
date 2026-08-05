"""Feature table for zone-hourly demand forecasting (SPEC-006).

Reuses `algorithms/timeseries/ewma_smoothing.py`'s `load_zone_hourly_blocks`
(already splits each zone's series into per-calendar-month blocks with no
Feb/Apr/May bridging -- see that module's docstring) rather than
re-implementing block splitting here.

Every derived feature (lag_1h, lag_24h, lag_168h, ewma, rolling_7d_avg) is
computed strictly from hours *before* t via `.shift(1)` (or the EWMA state
one step back) -- `ewma()` itself returns S_t which includes x_t, so using
it directly as a same-row feature would leak the target into its own
feature; shifting by 1 fixes that. Rows without a full 168-hour lag history
in their block (a boundary or block-start row) are dropped -- this is the
"respect block boundaries" requirement in FR-1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from algorithms.timeseries.ewma_smoothing import DEFAULT_ALPHA, ewma, load_zone_hourly_blocks  # noqa: E402

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"
ROLLING_WINDOW_H = 24 * 7


def _block_features(block: pd.Series, alpha: float) -> pd.DataFrame:
    s = ewma(block.to_numpy(dtype=float), alpha)
    ewma_lag1 = pd.Series(s, index=block.index).shift(1)
    rolling_7d_avg = block.shift(1).rolling(ROLLING_WINDOW_H, min_periods=24).mean()

    df = pd.DataFrame(
        {
            "total_trips": block,
            "lag_1h": block.shift(1),
            "lag_24h": block.shift(24),
            "lag_168h": block.shift(168),
            "ewma": ewma_lag1,
            "rolling_7d_avg": rolling_7d_avg,
        }
    )
    df["hour"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    return df.dropna()


def build_features(
    con: duckdb.DuckDBPyConnection, zone_ids: list[int] | None = None, alpha: float = DEFAULT_ALPHA
) -> pd.DataFrame:
    if zone_ids is None:
        zone_ids = (
            con.execute("SELECT DISTINCT pickup_location_id FROM zone_hourly_demand ORDER BY 1")
            .df()["pickup_location_id"]
            .tolist()
        )
    frames = []
    for zid in zone_ids:
        for block in load_zone_hourly_blocks(con, zid):
            feats = _block_features(block, alpha)
            if feats.empty:
                continue
            feats = feats.reset_index().rename(columns={"index": "ts"})
            feats["pickup_location_id"] = zid
            frames.append(feats)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "is_weekend",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "ewma",
    "rolling_7d_avg",
]
TARGET_COLUMN = "total_trips"


def demo() -> None:
    """Synthetic 2-block series; asserts no target leakage and block-boundary respect."""
    idx1 = pd.date_range("2024-01-01", periods=300, freq="h")
    idx2 = pd.date_range("2024-03-01", periods=300, freq="h")  # gap, separate block
    rng = pd.Series(range(300), dtype=float)
    block1 = pd.Series((rng % 24).to_numpy(), index=idx1)
    block2 = pd.Series((rng % 24).to_numpy() + 1, index=idx2)

    feats = pd.concat([_block_features(block1, DEFAULT_ALPHA), _block_features(block2, DEFAULT_ALPHA)])
    assert not feats.isna().any().any(), "no NaNs should survive dropna()"
    # leakage guard: lag_1h at row t must equal total_trips at t-1, never t
    for ts, row in feats.iterrows():
        prev_ts = ts - pd.Timedelta(hours=1)
        if prev_ts in block1.index:
            assert row["lag_1h"] == block1.loc[prev_ts]
    # first block should contribute rows only starting at hour 168 (0-indexed)
    assert feats.index.min() >= idx1[168]
    print(f"build_features demo OK: {len(feats)} feature rows from 2 blocks")


if __name__ == "__main__":
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    df = build_features(con)
    print(f"built {len(df)} feature rows across {df['pickup_location_id'].nunique()} zones")
    demo()
