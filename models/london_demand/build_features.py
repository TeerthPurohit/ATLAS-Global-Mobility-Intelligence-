"""Feature table for London station-hourly bike-share demand (SPEC-015 FR-4).

Mirrors `models/data_prep/build_features.py`'s lag/EWMA/rolling feature
shape exactly (same leakage discipline: every feature is computed strictly
from hours *before* t via `.shift(1)`) but reads `london_station_hourly_demand`
from the separately-attached `london_cycles.duckdb` instead of NYC's
`zone_hourly_demand`, and block-splits by station rather than by zone.

Block detection is gap-based here, not calendar-month-based like NYC's
`load_zone_hourly_blocks()`. Verified against the real data (see
`tests/test_london_demand_split_no_leakage.py`): London's 95 real dates are
NOT one continuous range -- they form three gapped blocks (2026-01-01..31,
2026-03-01..04-01, 2026-05-01..06-01), each of which happens to bleed one
day into the following calendar month, so grouping by calendar month like
NYC's loader does would incorrectly split the middle block in two. Detecting
blocks from actual date gaps (>1 day) is correct regardless of block
alignment with month boundaries.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from algorithms.timeseries.ewma_smoothing import DEFAULT_ALPHA, ewma  # noqa: E402

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "london_cycles.duckdb"
ROLLING_WINDOW_H = 24 * 7


def load_station_hourly_blocks(con: duckdb.DuckDBPyConnection, station_id: str) -> list[pd.Series]:
    """One pd.Series per contiguous date block of demand for a station.

    Missing hours *within* a block (zero departures that hour) are filled
    with 0, same as NYC's loader. Real date gaps (the Feb / most-of-April
    warehouse gaps) are detected from the data itself and never bridged."""
    df = con.execute(
        """
        SELECT trip_date, hour, total_trips
        FROM london_station_hourly_demand
        WHERE station_id = ?
        ORDER BY trip_date, hour
        """,
        [station_id],
    ).df()
    df["ts"] = pd.to_datetime(df["trip_date"]) + pd.to_timedelta(df["hour"], unit="h")
    series = df.set_index("ts")["total_trips"].sort_index()

    dates = pd.to_datetime(sorted(df["trip_date"].unique()))
    block_id = (dates.to_series().diff().dt.days.fillna(1) > 1).cumsum()
    date_to_block = dict(zip(dates, block_id))

    blocks = []
    for _, block_dates in pd.Series(date_to_block).groupby(pd.Series(date_to_block)):
        block_dates_idx = block_dates.index
        block_series = series[series.index.normalize().isin(block_dates_idx)]
        full_idx = pd.date_range(block_series.index.min(), block_series.index.max(), freq="h")
        blocks.append(block_series.reindex(full_idx, fill_value=0))
    return blocks


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
    con: duckdb.DuckDBPyConnection, station_ids: list[str] | None = None, alpha: float = DEFAULT_ALPHA
) -> pd.DataFrame:
    if station_ids is None:
        station_ids = (
            con.execute("SELECT DISTINCT station_id FROM london_station_hourly_demand ORDER BY 1")
            .df()["station_id"]
            .tolist()
        )
    frames = []
    for sid in station_ids:
        for block in load_station_hourly_blocks(con, sid):
            feats = _block_features(block, alpha)
            if feats.empty:
                continue
            feats = feats.reset_index().rename(columns={"index": "ts"})
            feats["station_id"] = sid
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
    """Synthetic 2-block series (mirrors NYC's build_features.py demo):
    asserts no target leakage and block-boundary respect."""
    idx1 = pd.date_range("2026-01-01", periods=300, freq="h")
    idx2 = pd.date_range("2026-03-01", periods=300, freq="h")  # gap, separate block
    rng = pd.Series(range(300), dtype=float)
    block1 = pd.Series((rng % 24).to_numpy(), index=idx1)
    block2 = pd.Series((rng % 24).to_numpy() + 1, index=idx2)

    feats = pd.concat([_block_features(block1, DEFAULT_ALPHA), _block_features(block2, DEFAULT_ALPHA)])
    assert not feats.isna().any().any(), "no NaNs should survive dropna()"
    for ts, row in feats.iterrows():
        prev_ts = ts - pd.Timedelta(hours=1)
        if prev_ts in block1.index:
            assert row["lag_1h"] == block1.loc[prev_ts]
    assert feats.index.min() >= idx1[168]
    print(f"london build_features demo OK: {len(feats)} feature rows from 2 blocks")


if __name__ == "__main__":
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    df = build_features(con)
    print(f"built {len(df)} feature rows across {df['station_id'].nunique()} stations")
    demo()
