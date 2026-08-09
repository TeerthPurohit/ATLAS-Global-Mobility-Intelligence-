"""Phase 10: leave-one-city-out "two-city transfer validation" (NEVER call
this "globally validated" -- only 2 real OBSERVED cities exist).

Same non-circularity requirement as Phase 1's population-scaling check
(`docs/cross_city_transfer_calibration.json`): refit everything using ONLY
the training city, then evaluate on the held-out city's own real measured
demand. The held-out city's demand never touches training in any of the
3 compared approaches.

Compared, per direction (train on one of {nyc, london}, eval on the other):
  1. Population scaling -- Phase 1's baseline, CITED not recomputed (task
     instruction: `docs/cross_city_transfer_calibration.json`'s
     `B_training_city_percapita_scaling` result already IS this, computed
     the same non-circular way).
  2. Global XGBoost (Phase 8's architecture) trained on ONLY the training
     city's rows, WITH city features (E_city) included as input columns
     (constant per row since there's only 1 training city, but still part
     of the feature vector the way it would be for a real multi-city fit).
  3. Same architecture, ablated WITHOUT city features -- isolates whether
     E_city helps at all beyond the temporal/weather features alone, given
     the eval city's own city features are unseen at fit time either way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import xgboost as xgb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from models.global_transfer.build_features import (  # noqa: E402
    CITY_FEATURE_COLUMNS,
    apply_scaler,
    build_city_feature_table,
    fit_scaler,
)
from models.global_transfer.train_global import (  # noqa: E402
    LONDON_DB,
    NYC_DB,
    SEED,
    TEMPORAL_FEATURE_COLUMNS,
    _temporal_features,
    load_city_hourly_total,
    rmse_mae,
)

CITED_POPULATION_SCALING_SOURCE = "docs/cross_city_transfer_calibration.json"


def _load_city_frame(city_id: str) -> pd.DataFrame:
    if city_id == "nyc":
        raw = load_city_hourly_total(NYC_DB, "zone_hourly_demand", "pickup_date", "pickup_hour")
    elif city_id == "london":
        raw = load_city_hourly_total(LONDON_DB, "london_station_hourly_demand", "trip_date", "hour")
    else:
        raise ValueError(city_id)
    feats = _temporal_features(raw).reset_index().rename(columns={"index": "ts"})
    feats["city_id"] = city_id
    return feats


def _attach_city_features(df: pd.DataFrame, scaler: dict) -> pd.DataFrame:
    con = duckdb.connect(str(NYC_DB), read_only=True)
    try:
        city_table = build_city_feature_table(con)
    finally:
        con.close()
    scaled = apply_scaler(city_table, scaler)
    return df.merge(scaled[["city_id"] + CITY_FEATURE_COLUMNS], on="city_id", how="left")


def _fit_predict(train: pd.DataFrame, eval_df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    model = xgb.XGBRegressor(max_depth=6, learning_rate=0.1, n_estimators=200, tree_method="hist",
                              random_state=SEED, n_jobs=-1)
    model.fit(train[feature_cols], train["total_trips"])
    return model.predict(eval_df[feature_cols])


def run_direction(train_city: str, eval_city: str, cited_population_scaling: dict) -> dict:
    train_df = _load_city_frame(train_city)
    eval_df = _load_city_frame(eval_city)

    # Fit the city-feature scaler on the TRAINING city only -- the held-out
    # city's feature vector is applied at inference but never touches the fit.
    con = duckdb.connect(str(NYC_DB), read_only=True)
    try:
        city_table = build_city_feature_table(con)
    finally:
        con.close()
    scaler = fit_scaler(city_table[city_table["city_id"] == train_city])

    train_wf = _attach_city_features(train_df, scaler)
    eval_wf = _attach_city_features(eval_df, scaler)

    with_city_feats = TEMPORAL_FEATURE_COLUMNS + CITY_FEATURE_COLUMNS
    ablation_no_city_feats = TEMPORAL_FEATURE_COLUMNS

    preds_with = _fit_predict(train_wf, eval_wf, with_city_feats)
    preds_ablation = _fit_predict(train_wf, eval_wf, ablation_no_city_feats)

    actual = eval_wf["total_trips"].to_numpy(dtype=float)
    rmse_with, mae_with = rmse_mae(actual, preds_with)
    rmse_abl, mae_abl = rmse_mae(actual, preds_ablation)

    return {
        "train_city": train_city,
        "eval_city": eval_city,
        "n_train_rows": len(train_wf),
        "n_eval_rows": len(eval_wf),
        "1_population_scaling_cited": {
            "source": CITED_POPULATION_SCALING_SOURCE,
            "wape_pct": cited_population_scaling["baselines"]["B_training_city_percapita_scaling"]["wape_pct"],
            "mae": cited_population_scaling["baselines"]["B_training_city_percapita_scaling"]["mae"],
            "note": (
                "cited, not recomputed -- see file for full methodology. Grain "
                "mismatch: this MAE is over DAILY city totals, while 2/3 below "
                "are over HOURLY city totals -- not directly comparable numbers, "
                "only directionally (both measure error against the same held-out "
                "city's real demand)."
            ),
        },
        "2_global_xgboost_with_city_features": {"rmse": rmse_with, "mae": mae_with},
        "3_global_xgboost_ablation_no_city_features": {"rmse": rmse_abl, "mae": mae_abl},
        "city_features_helped": bool(rmse_with < rmse_abl),
    }


def run_all() -> dict:
    cited_path = REPO_ROOT / CITED_POPULATION_SCALING_SOURCE
    cited = json.loads(cited_path.read_text())

    exp1 = run_direction("nyc", "london", cited["experiments"]["train_nyc_eval_london"])
    exp2 = run_direction("london", "nyc", cited["experiments"]["train_london_eval_nyc"])

    return {
        "label": "two-city transfer validation (NOT globally validated -- only 2 real OBSERVED cities exist)",
        "methodology": (
            "leave-one-city-out: train city's own data only fits everything "
            "(scaler + model); eval city's demand never touches training. "
            "Same non-circularity requirement as Phase 1's population-scaling check."
        ),
        "experiments": {"train_nyc_eval_london": exp1, "train_london_eval_nyc": exp2},
    }


def main() -> None:
    result = run_all()
    out_path = REPO_ROOT / "docs" / "global_transfer_model_comparison.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))
    for name, exp in result["experiments"].items():
        print(f"{name}: pop-scaling WAPE={exp['1_population_scaling_cited']['wape_pct']:.1f}%  "
              f"xgb+city_feats RMSE={exp['2_global_xgboost_with_city_features']['rmse']:.0f}  "
              f"xgb_ablation RMSE={exp['3_global_xgboost_ablation_no_city_features']['rmse']:.0f}  "
              f"city_features_helped={exp['city_features_helped']}")
    print(f"wrote {out_path}")


def demo() -> None:
    """Smallest runnable self-check: leave-one-city-out never lets the eval
    city's rows into the training frame."""
    train_df = _load_city_frame("nyc")
    eval_df = _load_city_frame("london")
    assert set(train_df["city_id"]) == {"nyc"}
    assert set(eval_df["city_id"]) == {"london"}
    print("model_comparison demo OK")


if __name__ == "__main__":
    demo()
    main()
