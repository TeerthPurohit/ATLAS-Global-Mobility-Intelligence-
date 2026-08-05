"""Linear regression baseline for zone-hourly demand (SPEC-006, FR-3).

Uses the feature table from `models/data_prep/build_features.py` as-is (no
one-hot expansion of hour/day_of_week -- 8 raw numeric features keeps the
coefficient table small enough to read and interpret directly, which is the
point of a baseline). Trained on train+val (no hyperparameters to tune here,
so val isn't needed for selection); test is touched only for final metrics.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.build_features import DEFAULT_DB_PATH, FEATURE_COLUMNS, TARGET_COLUMN, build_features  # noqa: E402
from data_prep.train_test_split import split_demand_blocks  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42  # no randomness in OLS, kept for the reproducibility record only


def rmse_mae(y_true, y_pred) -> tuple[float, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    return rmse, mae


def train_and_save(df: pd.DataFrame | None = None) -> dict:
    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con)

    train, val, test = split_demand_blocks(df, "ts")
    assert train["ts"].max() < val["ts"].min() < test["ts"].min(), "chronological split leaked"

    train_val = pd.concat([train, val])
    model = LinearRegression()
    model.fit(train_val[FEATURE_COLUMNS], train_val[TARGET_COLUMN])

    start = time.perf_counter()
    preds = model.predict(test[FEATURE_COLUMNS])
    latency_ms = (time.perf_counter() - start) / len(test) * 1000

    rmse, mae = rmse_mae(test[TARGET_COLUMN], preds)
    coefficients = dict(zip(FEATURE_COLUMNS, model.coef_.tolist()))

    import joblib

    joblib.dump(model, ARTIFACT_DIR / "linear_model.joblib")
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
        "hyperparameters": {},
        "coefficients": coefficients,
        "intercept": float(model.intercept_),
        "metrics": {"test_rmse": rmse, "test_mae": mae, "test_inference_latency_ms_per_row": latency_ms},
        "library_versions": {"sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "linear_model_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def interpret(coefficients: dict[str, float]) -> str:
    lines = []
    for feat, coef in sorted(coefficients.items(), key=lambda kv: -abs(kv[1])):
        direction = "increases" if coef > 0 else "decreases"
        lines.append(f"  {feat:16s} coef={coef:+.4f}  (+1 unit {direction} predicted trips by {abs(coef):.3f})")
    return "\n".join(lines)


if __name__ == "__main__":
    meta = train_and_save()
    print(f"test  RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
    print(f"inference latency: {meta['metrics']['test_inference_latency_ms_per_row']:.5f} ms/row")
    print("coefficients (sorted by |effect|):")
    print(interpret(meta["coefficients"]))
