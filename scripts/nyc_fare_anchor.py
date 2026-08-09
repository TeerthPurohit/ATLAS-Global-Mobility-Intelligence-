"""Real, measured NYC fare anchor shared by generate_tariff_profile.py and
calibrate_tariff_nyc.py (rules.md rule 1: fit a real regression before
reaching for an LLM at all, even for the anchor the LLM gets shown).

Least-squares fit of `total_amount ~ base + per_mile * trip_distance +
per_min * trip_duration_minutes` over a real sample of `int_trips_enriched`
rows -- the only place in this repo NYC's fare gets decomposed into a
linear base/per-mile/per-min structure (the trained XGBoost fare model
predicts `total_amount` directly and was never asked to decompose it, see
pricing_engine.py's module docstring).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
SAMPLE_ROWS = 200_000


def fit_nyc_fare_anchor(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    own_con = con is None
    if own_con:
        con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        df = con.execute(
            f"""
            SELECT trip_distance, trip_duration_minutes, total_amount
            FROM int_trips_enriched
            WHERE total_amount > 0 AND trip_distance > 0 AND trip_duration_minutes > 0
            USING SAMPLE {SAMPLE_ROWS} ROWS
            """
        ).df()
        # 5th percentile, not a bare min() -- a handful of rows have a
        # near-zero total_amount (a real data artifact, floating-point
        # noise around 0 that still passes ">0"), which would otherwise
        # make "minimum fare" a misleading ~$0.
        median_fare, min_fare = con.execute(
            "SELECT median(total_amount), quantile_cont(total_amount, 0.05) "
            "FROM int_trips_enriched WHERE total_amount > 0.5"
        ).fetchone()
    finally:
        if own_con:
            con.close()

    x = np.column_stack([np.ones(len(df)), df["trip_distance"].to_numpy(), df["trip_duration_minutes"].to_numpy()])
    y = df["total_amount"].to_numpy()
    coeffs, *_ = np.linalg.lstsq(x, y, rcond=None)
    base, per_mile, per_min = (float(c) for c in coeffs)
    return {
        "base_fare_usd": round(base, 2),
        "per_mile_usd": round(per_mile, 2),
        "per_min_usd": round(per_min, 2),
        "median_fare_usd": round(float(median_fare), 2),
        "min_fare_usd": round(float(min_fare), 2),
        "n_sampled": len(df),
    }


def demo() -> None:
    anchor = fit_nyc_fare_anchor()
    assert anchor["base_fare_usd"] > 0 and anchor["per_mile_usd"] > 0
    assert anchor["n_sampled"] > 1000
    print(f"NYC fare anchor: {anchor}")


if __name__ == "__main__":
    demo()
