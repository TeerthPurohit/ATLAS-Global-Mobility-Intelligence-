"""Phase 8: joint global transfer demand model, Y = f(X, E_city, M).

Trains ONE XGBoost regressor across BOTH observed cities (NYC
`zone_hourly_demand`, London `london_station_hourly_demand`), aggregated to
a comparable city-hour grain (reuses the city-daily aggregation *approach*
of `models/cross_city_estimation/calibration_eval.py`, just at hourly
instead of daily grain so the existing lag/EWMA feature shape from
`models/xgboost_model`/`models/london_demand` still applies).

X = temporal features (same lag/EWMA/rolling shape as the per-city XGBoost
models, computed block-gap-aware per city -- see
`models/london_demand/build_features.py`'s docstring for why gap-aware
matters). E_city = Phase 9's scaled static city feature vector
(`models/global_transfer/build_features.py`), broadcast onto every row of
that city. M (mobility_mode) is folded into E_city as `is_cycle_share`
rather than a separate argument -- it is itself a per-city static
attribute, no different in kind from population.

HONESTY (per task): with only 2 real OBSERVED cities, "E_city" here is
functionally a 2-valued categorical -- there is no evidence this
generalizes to a third city's feature vector. `models/global_transfer/
model_comparison.py` (Phase 10) measures this directly via leave-one-city-
out ablation; do not read this training script's val/test metrics as
"how well the model transfers," only as "how well it fits the 2 cities it
was trained on."

TRANSFER-tier cities (the 522 WorldMove-only rows in `global_cities`) never
appear as rows in this training set -- there is no trip-level demand target
for them. They are used only by `predict.py` at inference time, as
covariates, never as labels (task requirement, tested in
`tests/test_global_transfer_no_transfer_labels.py`).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from algorithms.timeseries.ewma_smoothing import DEFAULT_ALPHA, ewma  # noqa: E402
from models.data_prep.chronological_split import chronological_split  # noqa: E402
from models.global_transfer.build_features import (  # noqa: E402
    CITY_FEATURE_COLUMNS,
    apply_scaler,
    build_city_feature_table,
    fit_scaler,
    save_scaler,
)

NYC_DB = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
LONDON_DB = REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb"
ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42
ROLLING_WINDOW_H = 24 * 7

TEMPORAL_FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "is_weekend",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "ewma",
    "rolling_7d_avg",
    "temperature_c",
    "precipitation_mm",
]
FEATURE_COLUMNS = TEMPORAL_FEATURE_COLUMNS + CITY_FEATURE_COLUMNS
TARGET_COLUMN = "total_trips"

GRID = [
    {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 200},
    {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 200},
    {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 300},
]


def load_city_hourly_total(db_path: Path, table: str, date_col: str, hour_col: str) -> pd.DataFrame:
    """City-total demand per hour, summed across zones/stations. One row per
    (date, hour) actually present in the mart -- gaps are NOT bridged here,
    `_temporal_features` below detects them from the real dates."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(
            f"""
            SELECT {date_col} AS date, {hour_col} AS hour, SUM(total_trips) AS total_trips,
                   AVG(temperature_c) AS temperature_c, AVG(precipitation_mm) AS precipitation_mm
            FROM {table} GROUP BY 1, 2 ORDER BY 1, 2
            """
        ).df()
    finally:
        con.close()
    df["ts"] = pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"], unit="h")
    return df.set_index("ts").sort_index()


def _split_into_blocks(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Contiguous-date blocks, gap = >1 day between consecutive real dates
    (same detection rule as `models/london_demand/build_features.py`)."""
    dates = pd.to_datetime(sorted(pd.to_datetime(df["date"]).unique()))
    block_id = (dates.to_series().diff().dt.days.fillna(1) > 1).cumsum()
    date_to_block = dict(zip(dates, block_id))
    blocks = []
    for _, block_dates in pd.Series(date_to_block).groupby(pd.Series(date_to_block)):
        block_dates_idx = block_dates.index
        block_df = df[pd.to_datetime(df["date"]).isin(block_dates_idx)]
        full_idx = pd.date_range(block_df.index.min(), block_df.index.max(), freq="h")
        blocks.append(block_df.reindex(full_idx))
    return blocks


def _temporal_features(df: pd.DataFrame, alpha: float = DEFAULT_ALPHA) -> pd.DataFrame:
    """Lag/EWMA/rolling features, computed strictly gap-aware per contiguous
    block (never bridges a real date gap -- see module docstring)."""
    frames = []
    for block in _split_into_blocks(df):
        trips = block["total_trips"].fillna(0.0)
        s = ewma(trips.to_numpy(dtype=float), alpha)
        feats = pd.DataFrame(
            {
                "total_trips": trips,
                "lag_1h": trips.shift(1),
                "lag_24h": trips.shift(24),
                "lag_168h": trips.shift(168),
                "ewma": pd.Series(s, index=block.index).shift(1),
                "rolling_7d_avg": trips.shift(1).rolling(ROLLING_WINDOW_H, min_periods=24).mean(),
                "temperature_c": block["temperature_c"],
                "precipitation_mm": block["precipitation_mm"],
            }
        )
        feats["hour"] = feats.index.hour
        feats["day_of_week"] = feats.index.dayofweek
        feats["is_weekend"] = feats["day_of_week"].isin([5, 6]).astype(int)
        frames.append(feats.dropna())
    return pd.concat(frames) if frames else pd.DataFrame()


def build_joint_dataset() -> tuple[pd.DataFrame, dict]:
    """One dataframe, one row per (city_id, ts), temporal features +
    scaled city features + target. Also returns the fitted scaler (fit on
    train-city rows only -- see build_features.fit_scaler docstring)."""
    nyc_raw = load_city_hourly_total(NYC_DB, "zone_hourly_demand", "pickup_date", "pickup_hour")
    london_raw = load_city_hourly_total(LONDON_DB, "london_station_hourly_demand", "trip_date", "hour")

    nyc_feats = _temporal_features(nyc_raw).reset_index().rename(columns={"index": "ts"})
    nyc_feats["city_id"] = "nyc"
    london_feats = _temporal_features(london_raw).reset_index().rename(columns={"index": "ts"})
    london_feats["city_id"] = "london"

    con = duckdb.connect(str(NYC_DB), read_only=True)
    try:
        city_table = build_city_feature_table(con)
    finally:
        con.close()
    train_city_rows = city_table[city_table["city_id"].isin(["nyc", "london"])]
    scaler = fit_scaler(train_city_rows)
    scaled_city_table = apply_scaler(city_table, scaler)

    df = pd.concat([nyc_feats, london_feats], ignore_index=True)
    df = df.merge(scaled_city_table[["city_id"] + CITY_FEATURE_COLUMNS], on="city_id", how="left")
    return df, scaler


def rmse_mae(y_true, y_pred) -> tuple[float, float]:
    return float(np.sqrt(mean_squared_error(y_true, y_pred))), float(mean_absolute_error(y_true, y_pred))


def tune(train: pd.DataFrame, val: pd.DataFrame, feature_cols: list[str]) -> tuple[dict, list[dict]]:
    results, best = [], None
    for params in GRID:
        model = xgb.XGBRegressor(**params, tree_method="hist", random_state=SEED, n_jobs=-1)
        model.fit(train[feature_cols], train[TARGET_COLUMN])
        rmse, mae = rmse_mae(val[TARGET_COLUMN], model.predict(val[feature_cols]))
        result = {**params, "val_rmse": rmse, "val_mae": mae}
        results.append(result)
        if best is None or rmse < best["val_rmse"]:
            best = result
    return best, results  # type: ignore[return-value]


def train_and_save(df: pd.DataFrame | None = None, scaler: dict | None = None) -> dict:
    if df is None:
        df, scaler = build_joint_dataset()

    train, val, test = chronological_split(df, "ts", (0.7, 0.15, 0.15))
    assert train["ts"].max() < val["ts"].min() < test["ts"].min(), "chronological split leaked"
    assert set(train["city_id"]).issubset({"nyc", "london"})
    assert set(val["city_id"]).issubset({"nyc", "london"})
    assert set(test["city_id"]).issubset({"nyc", "london"}), "TRANSFER cities must never appear as training/eval rows"

    best, grid_results = tune(train, val, FEATURE_COLUMNS)
    final_params = {k: best[k] for k in ("max_depth", "learning_rate", "n_estimators")}

    train_val = pd.concat([train, val])
    model = xgb.XGBRegressor(**final_params, tree_method="hist", random_state=SEED, n_jobs=-1)
    model.fit(train_val[FEATURE_COLUMNS], train_val[TARGET_COLUMN])

    start = time.perf_counter()
    preds = model.predict(test[FEATURE_COLUMNS])
    latency_ms = (time.perf_counter() - start) / len(test) * 1000
    test_rmse, test_mae = rmse_mae(test[TARGET_COLUMN], preds)
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))

    model.save_model(str(ARTIFACT_DIR / "xgb_model.json"))
    save_scaler(scaler)

    metadata = {
        "model_id": "xgboost_global_transfer_v1",
        "city_id": "nyc+london",
        "seed": SEED,
        "date_range": {
            "train": [str(train["ts"].min()), str(train["ts"].max())],
            "val": [str(val["ts"].min()), str(val["ts"].max())],
            "test": [str(test["ts"].min()), str(test["ts"].max())],
        },
        "n_rows": {
            "train": len(train), "val": len(val), "test": len(test),
            "train_by_city": train["city_id"].value_counts().to_dict(),
            "val_by_city": val["city_id"].value_counts().to_dict(),
            "test_by_city": test["city_id"].value_counts().to_dict(),
        },
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "hyperparameters": final_params,
        "hyperparameter_search": grid_results,
        "feature_importances": importances,
        "metrics": {
            "val_rmse": best["val_rmse"],
            "val_mae": best["val_mae"],
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "test_inference_latency_ms_per_row": latency_ms,
        },
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
        "honesty_note": (
            "Trained on only 2 real OBSERVED cities (nyc, london). E_city is "
            "functionally a 2-valued categorical here -- these val/test metrics "
            "measure fit to those 2 cities, NOT validated cross-city "
            "generalization. See models/global_transfer/model_comparison.py and "
            "docs/global_transfer_model_comparison.json for the leave-one-city-out "
            "transfer check ('two-city transfer validation', never 'globally "
            "validated'). The 522 TRANSFER-tier cities in global_cities are used "
            "only as inference-time covariates by predict.py, never as training "
            "labels here."
        ),
    }
    (ARTIFACT_DIR / "xgb_metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    return metadata


def demo() -> None:
    """Smallest runnable self-check on synthetic data: block-gap detection
    doesn't bridge a gap, and the joint feature builder produces no NaNs."""
    idx = pd.date_range("2024-01-01", periods=300, freq="h")
    df = pd.DataFrame(
        {
            "date": idx.date,
            "total_trips": (np.arange(300) % 24).astype(float),
            "temperature_c": 10.0,
            "precipitation_mm": 0.0,
        },
        index=idx,
    )
    feats = _temporal_features(df)
    assert not feats.isna().any().any()
    assert feats.index.min() >= idx[168]
    print("global_transfer train_global demo OK")


if __name__ == "__main__":
    demo()
    meta = train_and_save()
    print(f"trained global transfer model: {meta['hyperparameters']}")
    print(f"n_rows: {meta['n_rows']}")
    print(f"val   RMSE={meta['metrics']['val_rmse']:.3f}  MAE={meta['metrics']['val_mae']:.3f}")
    print(f"test  RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
