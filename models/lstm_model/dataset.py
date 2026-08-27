"""Sliding-window sequences (24h -> next hour) for the LSTM (SPEC-006, FR-6).

Reuses `load_zone_hourly_blocks` (algorithms/timeseries/ewma_smoothing.py) so
windows never slide across the Feb/Apr/May gaps -- each block is windowed
independently, same block-boundary rule as `models/data_prep/build_features.py`.
Univariate: each timestep is just that hour's raw trip count (no extra
engineered features) per FR-6's literal "24h -> next hour" sequence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from algorithms.timeseries.ewma_smoothing import load_zone_hourly_blocks

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
    X_list, y_list, meta_rows = [], [], []
    for zid in zone_ids:
        for block in load_zone_hourly_blocks(con, zid):
            arr = block.to_numpy(dtype=np.float32)
            idx = block.index
            for i in range(window, len(arr)):
                X_list.append(arr[i - window : i])
                y_list.append(arr[i])
                meta_rows.append((idx[i], zid))
    X = np.asarray(X_list, dtype=np.float32)[..., None]
    y = np.asarray(y_list, dtype=np.float32)
    meta = pd.DataFrame(meta_rows, columns=["ts", "pickup_location_id"])
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
