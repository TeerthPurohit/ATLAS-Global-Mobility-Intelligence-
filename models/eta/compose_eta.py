"""Production ETA composition (Phase 7 spec): ETA = T_freeflow * C.

Deliberately NOT an opaque end-to-end ETA model -- T_freeflow comes from the
Phase 6 estimated free-flow lookup (`models/congestion/build_features.py`'s
`build_free_flow_lookup()`), and C is the Phase 6 trained congestion
multiplier model's point prediction. This keeps the free-flow/congestion
decomposition visible at inference time, per the spec's explicit instruction
not to hide it behind an opaque model unless proven more accurate (out of
scope here).

`models/backend/services/model_service.py`-style callers load
`congestion_model.json` once (rule 8: no live training on any serving
path) and pass a loaded `xgb.Booster`/`XGBRegressor` + free-flow lookup
DataFrame into `predict_eta()`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from congestion.build_features import FEATURE_COLUMNS, _bucket

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "congestion"


def free_flow_duration_min(trip_distance: float, free_flow_lookup: pd.DataFrame) -> float:
    """Look up the estimated free-flow duration for this trip's distance
    bucket. Raises if the distance falls in a bucket with no lookup row
    (too few historical trips at that distance to estimate free-flow speed)
    -- callers should treat that as `basis="unavailable"`, never silently
    fabricate a number."""
    bucket = _bucket(pd.Series([trip_distance])).iloc[0]
    row = free_flow_lookup.loc[free_flow_lookup["distance_bucket"] == bucket]
    if row.empty:
        raise ValueError(f"no free-flow lookup row for distance_bucket={bucket}")
    speed_mph = row["free_flow_speed_mph"].iloc[0]
    return trip_distance / speed_mph * 60.0


def predict_eta(features: dict, congestion_model: xgb.XGBRegressor, free_flow_lookup: pd.DataFrame) -> dict:
    """features must contain every key in FEATURE_COLUMNS (see
    models/congestion/build_features.py), including its own
    free_flow_duration_min (already computed via free_flow_duration_min()
    above and included as a model feature, same as at training time)."""
    row = pd.DataFrame([{c: features[c] for c in FEATURE_COLUMNS}])
    c_pred = float(congestion_model.predict(row)[0])
    t_freeflow = features["free_flow_duration_min"]
    eta_min = t_freeflow * c_pred
    return {
        "eta_minutes": eta_min,
        "free_flow_duration_min": t_freeflow,
        "congestion_multiplier": c_pred,
        "free_flow_source": "estimated",
    }


def demo() -> None:
    lookup = pd.DataFrame({"distance_bucket": [2.0], "free_flow_speed_mph": [12.0]})
    assert abs(free_flow_duration_min(2.0, lookup) - 10.0) < 1e-9

    class _StubModel:
        def predict(self, _row):
            return [1.5]

    features = {c: 0.0 for c in FEATURE_COLUMNS}
    features["free_flow_duration_min"] = 10.0
    result = predict_eta(features, _StubModel(), lookup)
    assert abs(result["eta_minutes"] - 15.0) < 1e-9, "ETA must equal T_freeflow * C exactly (composed, not opaque)"
    assert result["free_flow_source"] == "estimated"
    print("compose_eta demo OK")


if __name__ == "__main__":
    demo()
