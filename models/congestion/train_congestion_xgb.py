"""Train the congestion-multiplier XGBoost regressor (Phase 6).

Same tuned-grid-on-val pattern as `models/fare_prediction/train_fare_xgb.py`
and `models/xgboost_model/train_xgboost.py`. Split via
`models/data_prep/chronological_split.py`'s `split_demand_blocks()` -- not
reimplemented here.

`sample_rows=None` (train on the full ~113M-row corpus, project decision
2026-08-28) routes to `models/congestion/streaming_features.py`'s
external-memory path instead of this file's normal in-memory
`build_features()` + `XGBRegressor.fit()` path -- the full feature table
OOMs even on free-tier Colab if materialized in pandas at once (confirmed
empirically). Any explicit numeric `sample_rows` still goes through the
unchanged in-memory path.
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
from congestion.build_features import (
    DEFAULT_DB_PATH,
    FEATURE_COLUMNS,
    FREE_FLOW_PERCENTILE,
    TARGET_COLUMN,
    build_features,
)
from congestion.streaming_features import (
    TrainDataIter,
    count_split,
    load_streaming_context,
    materialize_split,
)
from data_prep.chronological_split import split_demand_blocks

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


def _booster_importances(booster: xgb.Booster) -> dict[str, float]:
    """`XGBRegressor.feature_importances_` normalizes gain to sum to 1;
    `Booster.get_score(importance_type='gain')` doesn't and omits
    zero-importance features -- reproduce the sklearn-wrapper shape so
    metadata is comparable between the in-memory and streaming paths."""
    raw = booster.get_score(importance_type="gain")
    total = sum(raw.values()) or 1.0
    return {f: raw.get(f, 0.0) / total for f in FEATURE_COLUMNS}


def _tune_streaming(con, bounds, lookups) -> tuple[dict, list[dict]]:
    val_df = materialize_split(con, "val", bounds, lookups)
    results = []
    best = None
    for params in GRID:
        it = TrainDataIter(con, bounds, lookups, split="train")
        dtrain = xgb.DMatrix(it)
        xgb_params = {"tree_method": "hist", "seed": SEED, "max_depth": params["max_depth"], "learning_rate": params["learning_rate"]}
        booster = xgb.train(xgb_params, dtrain, num_boost_round=params["n_estimators"])
        preds = booster.predict(xgb.DMatrix(val_df[FEATURE_COLUMNS]))
        rmse, mae = rmse_mae(val_df[TARGET_COLUMN], preds)
        result = {**params, "val_rmse": rmse, "val_mae": mae}
        results.append(result)
        if best is None or rmse < best["val_rmse"]:
            best = result
    return best, results, val_df


def _train_and_save_streaming() -> dict:
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    bounds, lookups = load_streaming_context(con)
    train_end, val_start, test_start = bounds

    best, grid_results, val_df = _tune_streaming(con, bounds, lookups)
    final_params = {k: best[k] for k in ("max_depth", "learning_rate", "n_estimators")}

    it = TrainDataIter(con, bounds, lookups, split="train_val")
    dtrain_val = xgb.DMatrix(it)
    xgb_params = {"tree_method": "hist", "seed": SEED, "max_depth": final_params["max_depth"], "learning_rate": final_params["learning_rate"]}
    booster = xgb.train(xgb_params, dtrain_val, num_boost_round=final_params["n_estimators"])

    test_df = materialize_split(con, "test", bounds, lookups)
    preds = booster.predict(xgb.DMatrix(test_df[FEATURE_COLUMNS]))
    test_rmse, test_mae = rmse_mae(test_df[TARGET_COLUMN], preds)
    importances = _booster_importances(booster)

    booster.save_model(str(ARTIFACT_DIR / "congestion_model.json"))
    metadata = {
        "seed": SEED,
        "sample_rows": None,
        "training_mode": "streaming_external_memory",
        "free_flow_source": "estimated",
        "free_flow_methodology": (
            f"per-distance-bucket ({FEATURE_COLUMNS[0]} bucketed at 0.5mi) "
            f"p{int(FREE_FLOW_PERCENTILE * 100)} of observed avg_speed_mph, i.e. the fastest observed "
            "trips at that distance approximate free-flow speed; NOT a measured/routed free-flow time "
            "-- see models/congestion/build_features.py module docstring for the full rationale, "
            "including the judgment call to use a high (not low) speed percentile"
        ),
        "date_range": {
            "train": ["(streamed, not materialized)", str(train_end)],
            "val": [str(val_start), str(test_start)],
            "test": [str(test_start), "(latest)"],
        },
        "n_rows": {
            # train: raw row count before transform_batch's filters (free-flow
            # bucket join, congestion_multiplier bounds, dropna) -- an upper
            # bound, not the exact post-transform count, since train is
            # streamed/never materialized as one frame to count exactly.
            "train_raw_upper_bound": count_split(con, "train", bounds),
            "val": len(val_df), "test": len(test_df),
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
        },
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "congestion_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def train_and_save(df: pd.DataFrame | None = None, sample_rows: int | None = 300_000) -> dict:
    if df is None and sample_rows is None:
        return _train_and_save_streaming()

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
        "training_mode": "in_memory",
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
