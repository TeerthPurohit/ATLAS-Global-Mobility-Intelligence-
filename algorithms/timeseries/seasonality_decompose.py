"""Trend + daily-seasonal + weekly-seasonal + residual decomposition, from scratch.

Multiplicative model: y_t = Trend_t * Daily_t * Weekly_t * Resid_t.

Chosen over additive by actually checking the data: for JFK Airport, East
Village, and Park Slope, the daily-cycle amplitude divided by the local
level stays roughly constant (~1.4-1.75x) even as the level itself drops
30-40% across the month (see `docs/adr` for the measured numbers). That's
the signature of multiplicative seasonality -- the swing scales with the
level -- not additive, where swing size would stay constant in absolute
trips regardless of level.

Same block handling as ewma_smoothing.py: Jan/Mar/Jun 2024 are the only
months present, decomposed independently -- trend/seasonal estimation never
smooths or averages across the Feb/Apr/May gaps.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd

from algorithms.timeseries.ewma_smoothing import WAREHOUSE_PATH, load_zone_hourly_blocks

TREND_WINDOW_HOURS = 169  # ~1 week, odd so the centered moving average has no half-step offset


@dataclass
class Decomposition:
    trend: np.ndarray
    daily: np.ndarray
    weekly: np.ndarray
    resid: np.ndarray
    index: pd.DatetimeIndex


def _centered_moving_average(x: np.ndarray, window: int) -> np.ndarray:
    """Centered MA via convolution; edges (window//2 on each side) are NaN, same
    convention as statsmodels' seasonal_decompose."""
    half = window // 2
    kernel = np.ones(window) / window
    ma = np.convolve(x, kernel, mode="valid")
    out = np.full_like(x, np.nan, dtype=float)
    out[half : half + len(ma)] = ma
    return out


def decompose(series: pd.Series, model: str = "multiplicative") -> Decomposition:
    x = series.to_numpy(dtype=float)
    trend = _centered_moving_average(x, TREND_WINDOW_HOURS)

    if model == "multiplicative":
        detrended = x / trend
    else:
        detrended = x - trend

    hours = series.index.hour.to_numpy()
    daily_by_hour = pd.Series(detrended).groupby(hours).mean()
    if model == "multiplicative":
        daily_by_hour /= daily_by_hour.mean()
    else:
        daily_by_hour -= daily_by_hour.mean()
    daily = daily_by_hour.reindex(hours).to_numpy()

    remainder = detrended / daily if model == "multiplicative" else detrended - daily

    dow = series.index.dayofweek.to_numpy()
    weekly_by_dow = pd.Series(remainder).groupby(dow).mean()
    if model == "multiplicative":
        weekly_by_dow /= weekly_by_dow.mean()
    else:
        weekly_by_dow -= weekly_by_dow.mean()
    weekly = weekly_by_dow.reindex(dow).to_numpy()

    resid = remainder / weekly if model == "multiplicative" else remainder - weekly
    return Decomposition(trend=trend, daily=daily, weekly=weekly, resid=resid, index=series.index)


def _plot_zone(block: pd.Series, decomp: Decomposition, name: str, out_path: str) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(block.index, block.to_numpy())
    axes[0].set_ylabel("observed")
    axes[1].plot(decomp.index, decomp.trend)
    axes[1].set_ylabel("trend")
    axes[2].plot(decomp.index, decomp.daily * decomp.weekly)
    axes[2].set_ylabel("daily*weekly")
    axes[3].plot(decomp.index, decomp.resid)
    axes[3].set_ylabel("resid")
    fig.suptitle(f"{name} — multiplicative decomposition (Jan 2024 block)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    import os

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    con = duckdb.connect(WAREHOUSE_PATH, read_only=True)
    for zone_id, name in [(132, "JFK Airport"), (79, "East Village"), (181, "Park Slope")]:
        blocks = load_zone_hourly_blocks(con, zone_id)
        jan_block = blocks[0]
        decomp = decompose(jan_block)
        reconstructed = decomp.trend * decomp.daily * decomp.weekly * decomp.resid
        valid = ~np.isnan(reconstructed)
        err = np.mean(np.abs(reconstructed[valid] - jan_block.to_numpy()[valid]))
        print(f"{name:15s} mean |reconstruction error| = {err:.6f} (expect ~0)")
        _plot_zone(jan_block, decomp, name, os.path.join(out_dir, f"{name.replace(' ', '_')}_decomp.png"))
    print(f"Plots saved to {out_dir}")
