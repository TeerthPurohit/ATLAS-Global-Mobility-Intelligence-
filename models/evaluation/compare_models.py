"""Evaluate all 4 demand models on one shared test set (SPEC-006, FR-7).

The tabular models (linear, EWMA, XGBoost) share the exact same feature
table and row set (`models/data_prep/build_features.py` +
`split_demand_blocks`, both keyed on 168h of lag warmup). The LSTM uses a
different representation (24h sliding windows, no 168h warmup needed) so it
has a few extra early-June rows the others don't. To make "identical test
rows" literal rather than aspirational, every model here is scored on the
inner join of (pickup_location_id, ts) across all four -- the intersection,
not a superset padded with NaNs.

Inference latency is measured fresh here, per model, with the same
batch-of-200 loop shape so the numbers are comparable to each other (not
copied from each model's own training-time measurement, which used
different batch sizes for the LSTM).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
import torch
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.build_features import DEFAULT_DB_PATH, FEATURE_COLUMNS, TARGET_COLUMN, build_features  # noqa: E402
from data_prep.train_test_split import split_demand_blocks  # noqa: E402
from lstm_model.dataset import build_sequences  # noqa: E402
from lstm_model.train_lstm import DemandLSTM  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent


def rmse_mae(y_true, y_pred) -> tuple[float, float]:
    return (
        float(np.sqrt(mean_squared_error(y_true, y_pred))),
        float(mean_absolute_error(y_true, y_pred)),
    )


def _measure_latency(probe) -> float:
    """probe() runs the model once on a small batch and returns the batch
    size; returns real measured ms/row, not an estimate."""
    start = time.perf_counter()
    n = probe()
    return (time.perf_counter() - start) / n * 1000


def evaluate_all() -> dict:
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)

    tab_df = build_features(con)
    _, _, tab_test = split_demand_blocks(tab_df, "ts")

    X_seq, y_seq, seq_meta = build_sequences(con)
    seq_meta = seq_meta.reset_index().rename(columns={"index": "_pos"})
    _, _, seq_test_m = split_demand_blocks(seq_meta, "ts")

    # intersection of (zone, ts) present in both representations' test sets
    key_cols = ["pickup_location_id", "ts"]
    common_keys = pd.merge(
        tab_test[key_cols].drop_duplicates(), seq_test_m[key_cols].drop_duplicates(), on=key_cols
    )
    tab_common = tab_test.merge(common_keys, on=key_cols)
    seq_common = seq_test_m.merge(common_keys, on=key_cols)
    assert len(tab_common) == len(seq_common) == len(common_keys)

    y_true = tab_common[TARGET_COLUMN].to_numpy()
    results = {}

    # --- Linear ---
    linear_model = joblib.load(ARTIFACT_DIR.parent / "linear_baseline" / "linear_model.joblib")
    X = tab_common[FEATURE_COLUMNS]
    preds = linear_model.predict(X)
    rmse, mae = rmse_mae(y_true, preds)
    lat = _measure_latency(lambda: (linear_model.predict(X.iloc[:200]), 200)[1])
    results["linear"] = {"rmse": rmse, "mae": mae, "latency_ms_per_row": lat, "n_rows": len(tab_common)}

    # --- EWMA (no model, forecast = its own `ewma` column) ---
    preds = tab_common["ewma"].to_numpy()
    rmse, mae = rmse_mae(y_true, preds)
    lat = _measure_latency(lambda: (tab_common["ewma"].iloc[:200].to_numpy(), 200)[1])
    results["ewma"] = {"rmse": rmse, "mae": mae, "latency_ms_per_row": lat, "n_rows": len(tab_common)}

    # --- XGBoost ---
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(ARTIFACT_DIR.parent / "xgboost_model" / "xgb_model.json"))
    preds = xgb_model.predict(X)
    rmse, mae = rmse_mae(y_true, preds)
    lat = _measure_latency(lambda: (xgb_model.predict(X.iloc[:200]), 200)[1])
    results["xgboost"] = {"rmse": rmse, "mae": mae, "latency_ms_per_row": lat, "n_rows": len(tab_common)}

    # --- LSTM ---
    lstm_meta = json.loads((ARTIFACT_DIR.parent / "lstm_model" / "lstm_metadata.json").read_text())
    y_mean, y_std = lstm_meta["target_scaling"]["mean"], lstm_meta["target_scaling"]["std"]
    model = DemandLSTM()
    model.load_state_dict(torch.load(ARTIFACT_DIR.parent / "lstm_model" / "lstm_model.pt"))
    model.eval()

    seq_pos = seq_common["_pos"].to_numpy()
    X_common_seq = (X_seq[seq_pos] - y_mean) / y_std
    with torch.no_grad():
        preds_norm = model(torch.from_numpy(X_common_seq)).numpy()
    preds = preds_norm * y_std + y_mean
    y_true_seq = y_seq[seq_pos]  # same underlying (zone, ts) rows as tab_common, via the join above
    rmse, mae = rmse_mae(y_true_seq, preds)

    def _lstm_latency_probe():
        with torch.no_grad():
            model(torch.from_numpy(X_common_seq[:200]))
        return 200

    lat = _measure_latency(_lstm_latency_probe)
    results["lstm"] = {"rmse": rmse, "mae": mae, "latency_ms_per_row": lat, "n_rows": len(seq_common)}

    return results


if __name__ == "__main__":
    results = evaluate_all()
    (ARTIFACT_DIR / "compare_results.json").write_text(json.dumps(results, indent=2))
    for name, m in results.items():
        print(
            f"{name:8s} RMSE={m['rmse']:.3f}  MAE={m['mae']:.3f}  "
            f"latency={m['latency_ms_per_row']:.5f} ms/row  n={m['n_rows']}"
        )
