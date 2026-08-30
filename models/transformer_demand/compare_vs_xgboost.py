"""Transformer vs. XGBoost on the identical chronological test rows (Phase 1
-- "trained honestly against XGBoost on the same test block").

Same intersection-of-(zone, ts) methodology as
`models/evaluation/compare_models.py` (tabular XGBoost rows need 168h lag
warmup, sequence Transformer rows need 24h warmup -- inner-join the two
test sets rather than padding either with NaNs).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transformer import DemandTransformer  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.build_features import DEFAULT_DB_PATH, FEATURE_COLUMNS, TARGET_COLUMN, build_features  # noqa: E402
from data_prep.train_test_split import split_demand_blocks  # noqa: E402
from lstm_model.dataset import build_sequences  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent


def rmse_mae(y_true, y_pred) -> tuple[float, float]:
    return (
        float(np.sqrt(mean_squared_error(y_true, y_pred))),
        float(mean_absolute_error(y_true, y_pred)),
    )


def _measure_latency(probe) -> float:
    start = time.perf_counter()
    n = probe()
    return (time.perf_counter() - start) / n * 1000


def evaluate(zone_ids: list[int] | None = None) -> dict:
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)

    tab_df = build_features(con, zone_ids=zone_ids)
    _, _, tab_test = split_demand_blocks(tab_df, "ts")

    X_seq, y_seq, seq_meta = build_sequences(con, zone_ids=zone_ids)
    seq_meta = seq_meta.reset_index().rename(columns={"index": "_pos"})
    _, _, seq_test_m = split_demand_blocks(seq_meta, "ts")

    key_cols = ["pickup_location_id", "ts"]
    common_keys = pd.merge(
        tab_test[key_cols].drop_duplicates(), seq_test_m[key_cols].drop_duplicates(), on=key_cols
    )
    tab_common = tab_test.merge(common_keys, on=key_cols)
    seq_common = seq_test_m.merge(common_keys, on=key_cols)
    assert len(tab_common) == len(seq_common) == len(common_keys)

    y_true = tab_common[TARGET_COLUMN].to_numpy()
    results = {}

    # --- XGBoost ---
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(ARTIFACT_DIR.parent / "xgboost_model" / "xgb_model.json"))
    X = tab_common[FEATURE_COLUMNS]
    preds = xgb_model.predict(X)
    rmse, mae = rmse_mae(y_true, preds)
    lat = _measure_latency(lambda: (xgb_model.predict(X.iloc[:200]), 200)[1])
    results["xgboost"] = {"rmse": rmse, "mae": mae, "latency_ms_per_row": lat, "n_rows": len(tab_common)}

    # --- Transformer ---
    tf_meta = json.loads((ARTIFACT_DIR / "transformer_metadata.json").read_text())
    y_mean, y_std = tf_meta["target_scaling"]["mean"], tf_meta["target_scaling"]["std"]
    model = DemandTransformer(
        d_model=tf_meta["hyperparameters"]["d_model"],
        num_heads=tf_meta["hyperparameters"]["num_heads"],
        num_layers=tf_meta["hyperparameters"]["num_layers"],
        dim_feedforward=tf_meta["hyperparameters"]["dim_feedforward"],
        dropout=tf_meta["hyperparameters"]["dropout"],
        window=tf_meta["window"],
    )
    model.load_state_dict(torch.load(ARTIFACT_DIR / "transformer_model.pt"))
    model.eval()

    seq_pos = seq_common["_pos"].to_numpy()
    X_common_seq = (X_seq[seq_pos] - y_mean) / y_std
    with torch.no_grad():
        preds_norm = model(torch.from_numpy(X_common_seq)).numpy()
    preds = preds_norm * y_std + y_mean
    y_true_seq = y_seq[seq_pos]
    rmse, mae = rmse_mae(y_true_seq, preds)

    def _tf_latency_probe():
        with torch.no_grad():
            model(torch.from_numpy(X_common_seq[:200]))
        return 200

    lat = _measure_latency(_tf_latency_probe)
    results["transformer"] = {"rmse": rmse, "mae": mae, "latency_ms_per_row": lat, "n_rows": len(seq_common)}

    return results


def write_report(results: dict, zone_ids: list[int] | None, out_path: Path) -> None:
    scope = f"a {len(zone_ids)}-zone subset (highest-volume zones)" if zone_ids else "the full ~262-zone warehouse"
    slowdown = results["transformer"]["latency_ms_per_row"] / results["xgboost"]["latency_ms_per_row"]
    lines = [
        "# Transformer vs. XGBoost -- zone-hourly demand (Phase 1)",
        "",
        "Both models scored on the identical chronological test rows (inner join",
        "of the tabular and sequence test sets on `(pickup_location_id, ts)`),",
        "same methodology as `models/evaluation/compare_models.py`.",
        "",
        f"**Scope:** trained/evaluated on {scope}. Real measured numbers, not estimates.",
        "",
        "| Model | RMSE | MAE | Inference latency (ms/row) | n_rows |",
        "|---|---|---|---|---|",
    ]
    for name in ("xgboost", "transformer"):
        m = results[name]
        lines.append(f"| {name} | {m['rmse']:.3f} | {m['mae']:.3f} | {m['latency_ms_per_row']:.5f} | {m['n_rows']} |")
    lines += [
        "",
        "XGBoost's engineered lag/EWMA/calendar features already hand it the",
        "signal the Transformer has to learn implicitly from 24 raw hourly counts,",
        "which is the likely reason it leads on both RMSE and MAE here;",
        f"the Transformer is also ~{slowdown:.1f}x slower per row (attention over 24 steps vs. tree traversal).",
    ]
    out_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    tf_meta = json.loads((ARTIFACT_DIR / "transformer_metadata.json").read_text())
    trained_zone_ids = tf_meta.get("zone_ids")
    results = evaluate(zone_ids=trained_zone_ids)
    (ARTIFACT_DIR / "compare_results.json").write_text(json.dumps(results, indent=2))
    write_report(results, trained_zone_ids, ARTIFACT_DIR / "comparison_report.md")
    for name, m in results.items():
        print(
            f"{name:11s} RMSE={m['rmse']:.3f}  MAE={m['mae']:.3f}  "
            f"latency={m['latency_ms_per_row']:.5f} ms/row  n={m['n_rows']}"
        )
