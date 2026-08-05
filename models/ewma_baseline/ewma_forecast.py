"""EWMA baseline for zone-hourly demand (SPEC-006, FR-4): no training.

The forecast for hour t is simply S_(t-1), the EWMA state one step back --
already computed as the `ewma` column in
`models/data_prep/build_features.py` (shifted by 1 there specifically so it
can be used as a same-row feature without leaking x_t into its own
prediction). This module just reads that column as the prediction; there is
no model to fit, so there are no hyperparameters beyond alpha (reused from
`algorithms/timeseries/ewma_smoothing.DEFAULT_ALPHA`).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.build_features import DEFAULT_DB_PATH, TARGET_COLUMN, build_features  # noqa: E402
from data_prep.train_test_split import split_demand_blocks  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from algorithms.timeseries.ewma_smoothing import DEFAULT_ALPHA  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent


def predict(df: pd.DataFrame) -> pd.Series:
    """Forecast for each row = its own `ewma` feature column (S_(t-1))."""
    return df["ewma"]


def evaluate_and_save(df: pd.DataFrame | None = None) -> dict:
    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con)

    train, val, test = split_demand_blocks(df, "ts")
    assert train["ts"].max() < val["ts"].min() < test["ts"].min(), "chronological split leaked"

    start = time.perf_counter()
    preds = predict(test)
    latency_ms = (time.perf_counter() - start) / len(test) * 1000

    rmse = float(np.sqrt(mean_squared_error(test[TARGET_COLUMN], preds)))
    mae = float(mean_absolute_error(test[TARGET_COLUMN], preds))

    metadata = {
        "seed": None,
        "note": "no training -- last known EWMA value used directly as the next-hour forecast",
        "hyperparameters": {"alpha": DEFAULT_ALPHA},
        "date_range": {
            "train": [str(train["ts"].min()), str(train["ts"].max())],
            "val": [str(val["ts"].min()), str(val["ts"].max())],
            "test": [str(test["ts"].min()), str(test["ts"].max())],
        },
        "n_rows": {"train": len(train), "val": len(val), "test": len(test)},
        "metrics": {"test_rmse": rmse, "test_mae": mae, "test_inference_latency_ms_per_row": latency_ms},
        "library_versions": {"pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "ewma_baseline_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    meta = evaluate_and_save()
    print(f"test  RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
    print(f"inference latency: {meta['metrics']['test_inference_latency_ms_per_row']:.5f} ms/row")
