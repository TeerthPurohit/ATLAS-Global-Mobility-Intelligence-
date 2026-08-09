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
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from congestion.build_features import DEFAULT_DB_PATH, FEATURE_COLUMNS, build_features  # noqa: E402
from data_prep.chronological_split import split_demand_blocks  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42
TARGET_COLUMN = "trip_duration_minutes"
QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}
XGB_PARAMS = {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300}


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


def train_and_save(df: pd.DataFrame | None = None, sample_rows: int | None = 300_000) -> dict:
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
        model.save_model(str(ARTIFACT_DIR / f"eta_{name}_model.json"))
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
            "n_test_rows": int(len(test)),
            "note": (
                "empirically measured fraction of held-out test rows where actual duration fell within "
                "[p10_pred, p90_pred] -- not assumed or hardcoded; see the gap vs nominal 0.80 above"
            ),
        },
        "ordering_violations_p10_p50_p90": ordering_violations,
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "eta_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    meta = train_and_save()
    print("pinball losses:", {k: round(v["pinball_loss"], 4) for k, v in meta["metrics"].items()})
    cov = meta["prediction_interval_coverage"]
    print(f"measured p10-p90 coverage: {cov['measured_p10_p90_coverage']:.4f} (nominal {cov['nominal']})")
    print(f"ordering violations (p10<=p50<=p90): {meta['ordering_violations_p10_p50_p90']}")
