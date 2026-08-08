"""Tuned XGBoost regressor for London station-hourly bike-share demand (SPEC-015 FR-4).

Mirrors `models/xgboost_model/train_xgboost.py`'s manual grid tuning and
reproducible metadata conventions (rule 3 chronological split, rule 5
reproducibility metadata).

Split discipline:
- Train + Val: Jan/Mar 2026 blocks (chronological 85/15 split on unique timestamps)
- Test: May 2026 block (held out entirely as test set)
- Assert train max ts < val min ts < test min ts to guarantee zero leakage.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from models.data_prep.train_test_split import chronological_split  # noqa: E402
from models.london_demand.build_features import (  # noqa: E402
    DEFAULT_DB_PATH,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_features,
)

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42
LONDON_TEST_BLOCK_START = "2026-05-01"

GRID = [
    {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 200},
    {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 200},
    {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 300},
    {"max_depth": 8, "learning_rate": 0.1, "n_estimators": 200},
]


def rmse_mae(y_true: pd.Series, y_pred: np.ndarray) -> tuple[float, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    return rmse, mae


def split_london_demand_blocks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_val = df[df["ts"] < LONDON_TEST_BLOCK_START]
    test = df[df["ts"] >= LONDON_TEST_BLOCK_START]
    train, val = chronological_split(train_val, "ts", (0.85, 0.15))
    return train, val, test


def tune(train: pd.DataFrame, val: pd.DataFrame) -> tuple[dict, list[dict]]:
    results = []
    best = None
    for params in GRID:
        model = xgb.XGBRegressor(**params, tree_method="hist", random_state=SEED, n_jobs=-1)
        model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN])
        rmse, mae = rmse_mae(val[TARGET_COLUMN], model.predict(val[FEATURE_COLUMNS]))
        result = {**params, "val_rmse": rmse, "val_mae": mae}
        results.append(result)
        if best is None or rmse < best["val_rmse"]:
            best = result
    return best, results  # type: ignore[return-value]


def train_and_save(df: pd.DataFrame | None = None) -> dict:
    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con)

    train, val, test = split_london_demand_blocks(df)
    assert train["ts"].max() < val["ts"].min() < test["ts"].min(), "chronological split leaked"

    best, grid_results = tune(train, val)
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
    metadata = {
        "model_id": "xgboost_london_demand_v1",
        "city_id": "london",
        "seed": SEED,
        "date_range": {
            "train": [str(train["ts"].min()), str(train["ts"].max())],
            "val": [str(val["ts"].min()), str(val["ts"].max())],
            "test": [str(test["ts"].min()), str(test["ts"].max())],
        },
        "n_rows": {"train": len(train), "val": len(val), "test": len(test)},
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
    }
    (ARTIFACT_DIR / "xgb_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    meta = train_and_save()
    print(f"London XGBoost model trained successfully. Hyperparameters: {meta['hyperparameters']}")
    print(f"val   RMSE={meta['metrics']['val_rmse']:.3f}  MAE={meta['metrics']['val_mae']:.3f}")
    print(f"test  RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
    print(f"Inference latency: {meta['metrics']['test_inference_latency_ms_per_row']:.5f} ms/row")
