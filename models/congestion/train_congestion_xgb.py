"""Train the congestion-multiplier XGBoost regressor (Phase 6).

Same tuned-grid-on-val pattern as `models/fare_prediction/train_fare_xgb.py`
and `models/xgboost_model/train_xgboost.py`. Split via
`models/data_prep/chronological_split.py`'s `split_demand_blocks()` -- not
reimplemented here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from congestion.build_features import (  # noqa: E402
    DEFAULT_DB_PATH,
    FEATURE_COLUMNS,
    FREE_FLOW_PERCENTILE,
    TARGET_COLUMN,
    build_features,
)
from data_prep.chronological_split import split_demand_blocks  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42

GRID = [
    {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 500},
]


def rmse_mae(y_true, y_pred) -> tuple[float, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    return rmse, mae


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
    return best, results


def train_and_save(df: pd.DataFrame | None = None, sample_rows: int | None = 300_000) -> dict:
    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con, sample_rows=sample_rows)
    else:
        sample_rows = "provided_externally"  # honesty: don't claim the default 300k when a caller (e.g. a test) passed its own df

    train, val, test = split_demand_blocks(df, "pickup_at")
    assert train["pickup_at"].max() < val["pickup_at"].min() < test["pickup_at"].min(), "chronological split leaked"

    best, grid_results = tune(train, val)
    final_params = {k: best[k] for k in ("max_depth", "learning_rate", "n_estimators")}

    train_val = pd.concat([train, val])
    model = xgb.XGBRegressor(**final_params, tree_method="hist", random_state=SEED, n_jobs=-1)
    model.fit(train_val[FEATURE_COLUMNS], train_val[TARGET_COLUMN])

    preds = model.predict(test[FEATURE_COLUMNS])
    test_rmse, test_mae = rmse_mae(test[TARGET_COLUMN], preds)
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))

    model.save_model(str(ARTIFACT_DIR / "congestion_model.json"))
    metadata = {
        "seed": SEED,
        "sample_rows": sample_rows,
        "free_flow_source": "estimated",
        "free_flow_methodology": (
            f"per-distance-bucket ({FEATURE_COLUMNS[0]} bucketed at 0.5mi) "
            f"p{int(FREE_FLOW_PERCENTILE * 100)} of observed avg_speed_mph, i.e. the fastest observed "
            "trips at that distance approximate free-flow speed; NOT a measured/routed free-flow time "
            "-- see models/congestion/build_features.py module docstring for the full rationale, "
            "including the judgment call to use a high (not low) speed percentile"
        ),
        "date_range": {
            "train": [str(train["pickup_at"].min()), str(train["pickup_at"].max())],
            "val": [str(val["pickup_at"].min()), str(val["pickup_at"].max())],
            "test": [str(test["pickup_at"].min()), str(test["pickup_at"].max())],
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
        },
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "congestion_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    meta = train_and_save()
    print(f"chosen hyperparameters: {meta['hyperparameters']}")
    print(f"val   RMSE={meta['metrics']['val_rmse']:.4f}  MAE={meta['metrics']['val_mae']:.4f}")
    print(f"test  RMSE={meta['metrics']['test_rmse']:.4f}  MAE={meta['metrics']['test_mae']:.4f}")
    print(f"free_flow_source: {meta['free_flow_source']}")
