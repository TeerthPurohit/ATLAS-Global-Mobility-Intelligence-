"""Quantile ETA models (Phase 7): eta_p10/p50/p90 via XGBoost's native
`reg:quantileerror` objective (pinball loss), one model per quantile
(xgboost>=2.0 supports `quantile_alpha` directly -- no need for 3 separate
architectures or a custom loss).

Target is the trip's actual observed duration (`trip_duration_minutes`),
same feature table as the Phase 6 congestion model
(`models/congestion/build_features.py` -- reused, not duplicated). These
quantile models are a direct empirical fit to observed duration; they are
NOT the production ETA path (see `compose_eta.py` for the explicit
T_freeflow * congestion_multiplier composition the spec asks for) -- they
exist to measure real prediction-interval coverage on held-out data.

Coverage is *measured*, not assumed: fraction of held-out test rows where
p10_pred <= actual <= p90_pred, reported honestly even if it misses the
nominal 80%.

`sample_rows=None` (train on the full ~113M-row corpus, project decision
2026-08-28) routes to `models/congestion/streaming_features.py`'s
external-memory path -- same reasoning as
`models/congestion/train_congestion_xgb.py`'s identical dispatch; the two
share this feature table and the OOM risk is the same.
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
from sklearn.metrics import mean_absolute_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from congestion.build_features import DEFAULT_DB_PATH, FEATURE_COLUMNS, build_features
from congestion.streaming_features import (
    TrainDataIter,
    count_split,
    load_streaming_context,
    materialize_split,
)
from data_prep.chronological_split import split_demand_blocks

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42
TARGET_COLUMN = "trip_duration_minutes"
QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}
XGB_PARAMS = {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300}
CHECKPOINT_PATH = ARTIFACT_DIR / "_streaming_checkpoint.json"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load_checkpoint() -> dict:
    """Resume state keyed on this run's own XGB_PARAMS -- NOT on whether
    eta_{name}_model.json merely exists. Bare file-existence was a real bug:
    tests/test_quantile_eta_ordering_and_coverage.py calls this module's
    non-streaming train_and_save() with a 20K-row sample df, which writes to
    these exact same production paths. A streaming run that resumed off
    file-existence alone silently scored a 20K-row-trained model against the
    real ~21M-row test set and reported that as the full-data result
    (caught 2026-08-28 by checking the log for "resuming from saved" against
    a run that should have been training fresh)."""
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"done": {}}  # name -> XGB_PARAMS it was actually trained with


def _save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    diff = y_true - y_pred
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1) * diff)))


def train_quantile(train: pd.DataFrame, alpha: float) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor(
        **XGB_PARAMS,
        objective="reg:quantileerror",
        quantile_alpha=alpha,
        tree_method="hist",
        random_state=SEED,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN])
    return model


def _train_and_save_streaming() -> dict:
    _log("connecting to warehouse")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    _log("computing split bounds + loading lookups")
    t0 = time.perf_counter()
    bounds, lookups = load_streaming_context(con)
    train_end, val_start, test_start = bounds
    _log(f"bounds/lookups ready in {time.perf_counter()-t0:.1f}s")

    _log("materializing test split")
    t0 = time.perf_counter()
    test_df = materialize_split(con, "test", bounds, lookups)
    _log(f"test split ready in {time.perf_counter()-t0:.1f}s: {len(test_df)} rows")

    state = _load_checkpoint()
    if state["done"]:
        _log(f"resuming from checkpoint: {sorted(state['done'])} already trained this run")

    preds = {}
    per_quantile_metrics = {}
    dtrain_val = None  # built once, lazily, and reused across quantiles -- same train_val
    # rows/features for all three, so re-scanning the ~90M-row split per quantile was pure waste
    for name, alpha in QUANTILES.items():
        model_path = ARTIFACT_DIR / f"eta_{name}_model.json"
        booster = xgb.Booster()
        if state["done"].get(name) == XGB_PARAMS and model_path.exists():
            _log(f"quantile {name} (alpha={alpha}) -- resuming from checkpoint ({model_path.name})")
            booster.load_model(str(model_path))
        else:
            _log(f"quantile {name} (alpha={alpha}) -- training")
            if dtrain_val is None:
                t0 = time.perf_counter()
                it = TrainDataIter(con, bounds, lookups, split="train_val")
                # QuantileDMatrix (not plain DMatrix) builds hist bins directly from
                # the iterator on-device -- the memory-efficient, GPU-native path
                # `tree_method="hist"`/device="cuda" expects; plain DMatrix stages a
                # full CPU-side copy first.
                dtrain_val = xgb.QuantileDMatrix(it)
                _log(f"train_val QuantileDMatrix materialized in {time.perf_counter()-t0:.1f}s (shared across remaining quantiles)")
            t0 = time.perf_counter()
            xgb_params = {
                **{k: v for k, v in XGB_PARAMS.items() if k != "n_estimators"},
                "objective": "reg:quantileerror", "quantile_alpha": alpha,
                "tree_method": "hist", "device": "cuda", "seed": SEED,
            }
            booster = xgb.train(xgb_params, dtrain_val, num_boost_round=XGB_PARAMS["n_estimators"])
            _log(f"quantile {name} trained in {time.perf_counter()-t0:.1f}s")
            # Save immediately, before scoring -- same reasoning as
            # congestion's identical fix: a multi-hour training step must
            # never be thrown away by a failure in the comparatively cheap
            # test-set prediction that follows.
            booster.save_model(str(model_path))
            state["done"][name] = XGB_PARAMS
            _save_checkpoint(state)
            _log(f"quantile {name} model saved")

        p = booster.predict(xgb.DMatrix(test_df[FEATURE_COLUMNS]))
        preds[name] = p
        per_quantile_metrics[name] = {
            "alpha": alpha,
            "pinball_loss": pinball_loss(test_df[TARGET_COLUMN].to_numpy(), p, alpha),
            "mae": float(mean_absolute_error(test_df[TARGET_COLUMN], p)),
        }
        _log(f"quantile {name} scored: pinball_loss={per_quantile_metrics[name]['pinball_loss']:.4f}")

    actual = test_df[TARGET_COLUMN].to_numpy()
    within_interval = (actual >= preds["p10"]) & (actual <= preds["p90"])
    coverage = float(np.mean(within_interval))
    ordering_violations = int(np.sum((preds["p10"] > preds["p50"]) | (preds["p50"] > preds["p90"])))

    metadata = {
        "seed": SEED,
        "sample_rows": None,
        "training_mode": "streaming_external_memory",
        "date_range": {
            "train": ["(streamed, not materialized)", str(train_end)],
            "val": [str(val_start), str(test_start)],
            "test": [str(test_start), "(latest)"],
        },
        "n_rows": {"train_val_raw_upper_bound": count_split(con, "train_val", bounds), "test": len(test_df)},
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "hyperparameters": XGB_PARAMS,
        "quantiles": QUANTILES,
        "metrics": per_quantile_metrics,
        "prediction_interval_coverage": {
            "nominal": 0.80,
            "measured_p10_p90_coverage": coverage,
            "n_test_rows": int(len(test_df)),  # noqa: RUF046
            "note": (
                "empirically measured fraction of held-out test rows where actual duration fell within "
                "[p10_pred, p90_pred] -- not assumed or hardcoded; see the gap vs nominal 0.80 above"
            ),
        },
        "ordering_violations_p10_p50_p90": ordering_violations,
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "eta_metadata.json").write_text(json.dumps(metadata, indent=2))
    CHECKPOINT_PATH.unlink(missing_ok=True)  # full success -- resume state no longer needed
    _log("eta training complete")
    return metadata


def train_and_save(
    df: pd.DataFrame | None = None, sample_rows: int | None = 300_000, output_dir: Path = ARTIFACT_DIR
) -> dict:
    if df is None and sample_rows is None:
        return _train_and_save_streaming()

    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con, sample_rows=sample_rows)
    else:
        sample_rows = "provided_externally"  # honesty: don't claim the default 300k when a caller (e.g. a test) passed its own df

    train, val, test = split_demand_blocks(df, "pickup_at")
    assert train["pickup_at"].max() < val["pickup_at"].min() < test["pickup_at"].min(), "chronological split leaked"
    train_val = pd.concat([train, val])

    preds = {}
    per_quantile_metrics = {}
    for name, alpha in QUANTILES.items():
        model = train_quantile(train_val, alpha)
        model.save_model(str(output_dir / f"eta_{name}_model.json"))
        p = model.predict(test[FEATURE_COLUMNS])
        preds[name] = p
        per_quantile_metrics[name] = {
            "alpha": alpha,
            "pinball_loss": pinball_loss(test[TARGET_COLUMN].to_numpy(), p, alpha),
            "mae": float(mean_absolute_error(test[TARGET_COLUMN], p)),
        }

    actual = test[TARGET_COLUMN].to_numpy()
    within_interval = (actual >= preds["p10"]) & (actual <= preds["p90"])
    coverage = float(np.mean(within_interval))
    ordering_violations = int(np.sum((preds["p10"] > preds["p50"]) | (preds["p50"] > preds["p90"])))

    metadata = {
        "seed": SEED,
        "sample_rows": sample_rows,
        "training_mode": "in_memory",
        "date_range": {
            "train": [str(train["pickup_at"].min()), str(train["pickup_at"].max())],
            "val": [str(val["pickup_at"].min()), str(val["pickup_at"].max())],
            "test": [str(test["pickup_at"].min()), str(test["pickup_at"].max())],
        },
        "n_rows": {"train": len(train), "val": len(val), "test": len(test)},
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "hyperparameters": XGB_PARAMS,
        "quantiles": QUANTILES,
        "metrics": per_quantile_metrics,
        "prediction_interval_coverage": {
            "nominal": 0.80,
            "measured_p10_p90_coverage": coverage,
            "n_test_rows": int(len(test)),  # noqa: RUF046
            "note": (
                "empirically measured fraction of held-out test rows where actual duration fell within "
                "[p10_pred, p90_pred] -- not assumed or hardcoded; see the gap vs nominal 0.80 above"
            ),
        },
        "ordering_violations_p10_p50_p90": ordering_violations,
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (output_dir / "eta_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    meta = train_and_save()
    print("pinball losses:", {k: round(v["pinball_loss"], 4) for k, v in meta["metrics"].items()})
    cov = meta["prediction_interval_coverage"]
    print(f"measured p10-p90 coverage: {cov['measured_p10_p90_coverage']:.4f} (nominal {cov['nominal']})")
    print(f"ordering violations (p10<=p50<=p90): {meta['ordering_violations_p10_p50_p90']}")
