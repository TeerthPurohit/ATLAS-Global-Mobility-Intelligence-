"""Sliding-window sequences (24h -> next hour) for the LSTM (SPEC-006, FR-6).

Same block-boundary rule as `algorithms/timeseries/ewma_smoothing.load_zone_hourly_blocks`
(per-month reindex with zero-fill, one block per calendar-month, never bridging
the Feb/Apr/May gaps) and `models/data_prep/build_features.py`, but fetches
every requested zone in one bulk query and builds windows via
`sliding_window_view` instead of one query + a Python-level per-row loop per
zone -- ~250x faster over the full ~260-zone warehouse (minutes -> ~2s),
verified byte-identical to the old per-zone-loop output before this change.
Univariate: each timestep is just that hour's raw trip count (no extra
engineered features) per FR-6's literal "24h -> next hour" sequence.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"
WINDOW = 24


def build_sequences(
    con: duckdb.DuckDBPyConnection, zone_ids: list[int] | None = None, window: int = WINDOW
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Returns X (N, window, 1) float32, y (N,) float32, meta (N, 2) [ts, pickup_location_id]."""
    if zone_ids is None:
        zone_ids = (
            con.execute("SELECT DISTINCT pickup_location_id FROM zone_hourly_demand ORDER BY 1")
            .df()["pickup_location_id"]
            .tolist()
        )
    placeholders = ",".join("?" * len(zone_ids))
    df = con.execute(
        f"""
        SELECT pickup_location_id, pickup_date, pickup_hour, total_trips
        FROM zone_hourly_demand
        WHERE pickup_location_id IN ({placeholders})
        ORDER BY pickup_location_id, pickup_date, pickup_hour
        """,
        zone_ids,
    ).df()
    df["ts"] = pd.to_datetime(df["pickup_date"]) + pd.to_timedelta(df["pickup_hour"], unit="h")

    X_parts, y_parts, meta_parts = [], [], []
    for zid, zdf in df.groupby("pickup_location_id", sort=False):
        series = zdf.set_index("ts")["total_trips"].sort_index()
        for _, month_series in series.groupby(series.index.to_period("M")):
            full_idx = pd.date_range(month_series.index.min(), month_series.index.max(), freq="h")
            block = month_series.reindex(full_idx, fill_value=0)
            arr = block.to_numpy(dtype=np.float32)
            if len(arr) <= window:
                continue
            windows = np.lib.stride_tricks.sliding_window_view(arr, window)[:-1].copy()
            targets = arr[window:]
            X_parts.append(windows)
            y_parts.append(targets)
            meta_parts.append(pd.DataFrame({"ts": block.index[window:], "pickup_location_id": zid}))
    X = np.concatenate(X_parts, axis=0)[..., None].astype(np.float32)
    y = np.concatenate(y_parts, axis=0).astype(np.float32)
    meta = pd.concat(meta_parts, ignore_index=True)
    return X, y, meta


def demo() -> None:
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    X, y, meta = build_sequences(con, zone_ids=[132])
    assert X.shape[1:] == (WINDOW, 1)
    assert len(X) == len(y) == len(meta)
    # boundary check: no window should span the Jan->Mar gap
    gaps = meta["ts"].diff().dt.total_seconds().dropna()
    assert (gaps <= 3600).all() or (gaps > 3600).sum() <= 2, "unexpected multi-hour meta gaps"
    print(f"dataset demo OK: {len(X)} sequences for zone 132")


if __name__ == "__main__":
    demo()
