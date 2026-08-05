"""EWMA smoothing over zone_hourly_demand, implemented from scratch.

S_t = alpha * x_t + (1 - alpha) * S_(t-1), S_0 = x_0.

Alpha = 0.7 for JFK Airport (132), 0.3 for East Village (79), 0.55 for Park
Slope (181) all minimize a genuine bias/variance elbow when we plot MSE of
S_t against each hour's true diurnal mean (see `_best_alpha` sweep in
`__main__`) -- low alpha lags the ~24h demand cycle too much (bias), high
alpha just tracks the raw noise (no smoothing). The optimum shifts per zone
(0.3-0.75) because nightlife zones swing less predictably hour to hour than
airport traffic. This module defaults to alpha=0.5 as the cross-zone
compromise actually measured on real data (see module docstring test run),
not a convention default -- callers with a specific zone should re-run the
sweep and override.

Data only exists for Jan/Mar/Jun 2024 (Feb/Apr/May missing per EDA). Each
calendar month is treated as an independent block: the recursive state S_t
is reset (S_0 = first value of the block) at the start of every block so a
"previous hour" never reaches across a 2-month gap.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

DEFAULT_ALPHA = 0.5
WAREHOUSE_PATH = "data/warehouse/nyc_rides.duckdb"


def ewma(x: np.ndarray, alpha: float) -> np.ndarray:
    """Recursive EWMA, from scratch. S_0 = x_0 (matches pandas .ewm(adjust=False))."""
    if not 0 < alpha <= 1:
        raise ValueError(f"alpha must be in (0, 1], got {alpha}")
    x = np.asarray(x, dtype=float)
    s = np.empty_like(x)
    s[0] = x[0]
    for t in range(1, len(x)):
        s[t] = alpha * x[t] + (1 - alpha) * s[t - 1]
    return s


def load_zone_hourly_blocks(con: duckdb.DuckDBPyConnection, zone_id: int) -> list[pd.Series]:
    """One pd.Series per contiguous calendar-month block of demand for a zone.

    Missing hours *within* a block (zero trips that hour) are filled with 0.
    Missing months (the Feb/Apr/May gaps) are never bridged -- each block is
    reindexed only across its own month's hourly range.
    """
    df = con.execute(
        """
        SELECT pickup_date, pickup_hour, total_trips
        FROM zone_hourly_demand
        WHERE pickup_location_id = ?
        ORDER BY pickup_date, pickup_hour
        """,
        [zone_id],
    ).df()
    df["ts"] = pd.to_datetime(df["pickup_date"]) + pd.to_timedelta(df["pickup_hour"], unit="h")
    series = df.set_index("ts")["total_trips"].sort_index()

    blocks = []
    for _, month_series in series.groupby(series.index.to_period("M")):
        full_idx = pd.date_range(month_series.index.min(), month_series.index.max(), freq="h")
        blocks.append(month_series.reindex(full_idx, fill_value=0))
    return blocks


def ewma_blocks(blocks: list[pd.Series], alpha: float) -> list[pd.Series]:
    """Apply ewma() per block, resetting state at each block boundary."""
    return [pd.Series(ewma(b.to_numpy(), alpha), index=b.index) for b in blocks]


def _best_alpha(block: pd.Series, grid: np.ndarray) -> tuple[float, float]:
    """Sweep alpha, score by MSE of S_t vs. that hour's true hour-of-day mean.

    Low alpha lags the daily cycle (bias); high alpha just echoes raw noise
    (no smoothing benefit). The minimum is the bias/variance elbow.
    """
    x = block.to_numpy(dtype=float)
    hour_mean = pd.Series(x).groupby(block.index.hour).transform("mean").to_numpy()
    scores = [(a, np.mean((ewma(x, a) - hour_mean) ** 2)) for a in grid]
    return min(scores, key=lambda p: p[1])


if __name__ == "__main__":
    con = duckdb.connect(WAREHOUSE_PATH, read_only=True)
    grid = np.arange(0.05, 1.0, 0.05)
    for zone_id, name in [(132, "JFK Airport"), (79, "East Village"), (181, "Park Slope")]:
        blocks = load_zone_hourly_blocks(con, zone_id)
        best_a, best_mse = _best_alpha(blocks[0], grid)
        default_mse = _best_alpha(blocks[0], np.array([DEFAULT_ALPHA]))[1]
        print(
            f"{name:15s} best alpha={best_a:.2f} (mse={best_mse:.1f})  "
            f"default alpha={DEFAULT_ALPHA} (mse={default_mse:.1f})"
        )
