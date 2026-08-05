"""Tuned XGBoost regressor for zone-hourly demand (SPEC-006, FR-5).

Same manual-grid-tuned-on-val pattern as
`models/fare_prediction/train_fare_xgb.py` (small grid over
depth/learning_rate/n_estimators, selected by validation RMSE, refit on
train+val, test touched once). Feature importances are saved alongside the
linear baseline's coefficients so `compare_models.py` / the metrics report
can put them side by side.
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
from data_prep.build_features import DEFAULT_DB_PATH, FEATURE_COLUMNS, TARGET_COLUMN, build_features  # noqa: E402
from data_prep.train_test_split import split_demand_blocks  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42

GRID = [
    {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 500},
    {"max_depth": 8, "learning_rate": 0.1, "n_estimators": 300},
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


def train_and_save(df: pd.DataFrame | None = None) -> dict:
    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con)

    train, val, test = split_demand_blocks(df, "ts")
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


def plot_feature_importance(metadata: dict, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    importances = metadata["feature_importances"]
    feats = sorted(importances, key=lambda f: importances[f])
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(feats, [importances[f] for f in feats])
    ax.set_xlabel("XGBoost feature importance (gain-based, default)")
    ax.set_title("Zone-hourly demand: XGBoost feature importance")
    fig.tight_layout()
    fig.savefig(out_path)


if __name__ == "__main__":
    meta = train_and_save()
    print(f"chosen hyperparameters: {meta['hyperparameters']}")
    print(f"val   RMSE={meta['metrics']['val_rmse']:.3f}  MAE={meta['metrics']['val_mae']:.3f}")
    print(f"test  RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
    print(f"inference latency: {meta['metrics']['test_inference_latency_ms_per_row']:.5f} ms/row")
    print("feature importances:", json.dumps(meta["feature_importances"], indent=2))
    plot_feature_importance(meta, ARTIFACT_DIR / "feature_importance.png")
