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
import time
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
CHECKPOINT_PATH = ARTIFACT_DIR / "_streaming_checkpoint.json"

GRID = [
    {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 500},
]


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load_checkpoint() -> dict:
    """Resume state for the streaming path only -- a multi-hour run (grid
    search + final refit) failing on the cheap, fast test-eval step at the
    very end must not throw away everything before it. `grid_results`
    accumulates one entry per completed GRID candidate (matched by params,
    so this stays correct if GRID's order/contents change between runs);
    `final_model` records the hyperparameters the currently-saved
    congestion_model.json was actually trained with, so a fresh run only
    redoes the refit if that doesn't match this run's chosen best params."""
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"grid_results": [], "final_model": None}


def _save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


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


def _tune_streaming(con, bounds, lookups, state: dict) -> tuple[dict, list[dict]]:
    _log("materializing val split")
    val_df = materialize_split(con, "val", bounds, lookups)
    _log(f"val split ready: {len(val_df)} rows")

    done_by_params = {json.dumps(r["params"], sort_keys=True): r for r in state["grid_results"]}
    results = []
    best = None
    for i, params in enumerate(GRID, 1):
        key = json.dumps(params, sort_keys=True)
        if key in done_by_params:
            result = done_by_params[key]["result"]
            _log(f"grid candidate {i}/{len(GRID)} {params} -- resumed from checkpoint, val_rmse={result['val_rmse']:.4f}")
        else:
            _log(f"grid candidate {i}/{len(GRID)} {params} -- training")
            t0 = time.perf_counter()
            it = TrainDataIter(con, bounds, lookups, split="train")
            dtrain = xgb.DMatrix(it)
            xgb_params = {"tree_method": "hist", "seed": SEED, "max_depth": params["max_depth"], "learning_rate": params["learning_rate"]}
            booster = xgb.train(xgb_params, dtrain, num_boost_round=params["n_estimators"])
            preds = booster.predict(xgb.DMatrix(val_df[FEATURE_COLUMNS]))
            rmse, mae = rmse_mae(val_df[TARGET_COLUMN], preds)
            result = {**params, "val_rmse": rmse, "val_mae": mae}
            _log(f"grid candidate {i}/{len(GRID)} done in {time.perf_counter()-t0:.1f}s: val_rmse={rmse:.4f} val_mae={mae:.4f}")
            state["grid_results"].append({"params": params, "result": result})
            _save_checkpoint(state)
        results.append(result)
        if best is None or result["val_rmse"] < best["val_rmse"]:
            best = result
    return best, results, val_df


def _train_and_save_streaming() -> dict:
    _log("connecting to warehouse")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    state = _load_checkpoint()
    if state["grid_results"] or state["final_model"]:
        _log(f"resuming from checkpoint: {len(state['grid_results'])} grid candidate(s), final_model={'saved' if state['final_model'] else 'not yet'}")

    _log("computing split bounds + loading lookups")
    t0 = time.perf_counter()
    bounds, lookups = load_streaming_context(con)
    train_end, val_start, test_start = bounds
    _log(f"bounds/lookups ready in {time.perf_counter()-t0:.1f}s: train_end={train_end} val_start={val_start} test_start={test_start}")

    best, grid_results, val_df = _tune_streaming(con, bounds, lookups, state)
    final_params = {k: best[k] for k in ("max_depth", "learning_rate", "n_estimators")}
    _log(f"grid search complete, best={final_params}")

    model_path = ARTIFACT_DIR / "congestion_model.json"
    if state["final_model"] == final_params and model_path.exists():
        _log("final refit already done for these hyperparameters -- loading saved model instead of retraining")
        booster = xgb.Booster()
        booster.load_model(str(model_path))
    else:
        _log("training final refit on train+val")
        t0 = time.perf_counter()
        it = TrainDataIter(con, bounds, lookups, split="train_val")
        dtrain_val = xgb.DMatrix(it)
        xgb_params = {"tree_method": "hist", "seed": SEED, "max_depth": final_params["max_depth"], "learning_rate": final_params["learning_rate"]}
        booster = xgb.train(xgb_params, dtrain_val, num_boost_round=final_params["n_estimators"])
        _log(f"final refit done in {time.perf_counter()-t0:.1f}s")

        # Save immediately -- this is the expensive part (a multi-hour external-memory
        # refit). Everything after this point (test-set scoring) is comparatively
        # cheap and must never be able to lose the trained model if it fails --
        # confirmed the hard way: a 3-hour run's booster.predict() on the test set
        # hit XGBoostError: bad allocation and the old save-after-eval order threw
        # the whole run away for a failure in an unrelated, much cheaper step.
        booster.save_model(str(model_path))
        state["final_model"] = final_params
        _save_checkpoint(state)
        _log("model saved")

    importances = _booster_importances(booster)

    _log("materializing test split + scoring")
    t0 = time.perf_counter()
    test_df = materialize_split(con, "test", bounds, lookups)
    preds = booster.predict(xgb.DMatrix(test_df[FEATURE_COLUMNS]))
    test_rmse, test_mae = rmse_mae(test_df[TARGET_COLUMN], preds)
    _log(f"test scoring done in {time.perf_counter()-t0:.1f}s: test_rmse={test_rmse:.4f} test_mae={test_mae:.4f}")

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
    CHECKPOINT_PATH.unlink(missing_ok=True)  # full success -- resume state no longer needed
    _log("congestion training complete")
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
