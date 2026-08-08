"""Loads precomputed model artifacts once at startup (rule 8 — no training or
raw-table scans on a request path). Call `load()` from a FastAPI startup hook
before the app accepts traffic; routers call the `predict_*` functions only.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import duckdb
import pandas as pd
import xgboost as xgb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from algorithms.spatial.kdtree_zone_lookup import load_zone_points  # noqa: E402
from data_prep.build_features import FEATURE_COLUMNS, build_features  # noqa: E402

DEMAND_MODEL_PATH = REPO_ROOT / "models" / "xgboost_model" / "xgb_model.json"
FARE_MODEL_PATH = REPO_ROOT / "models" / "fare_prediction" / "fare_xgb_model.json"
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

DEMAND_MODEL_NAME = "xgboost_demand_v1"
EWMA_FALLBACK_NAME = "ewma_fallback_v1"
FARE_MODEL_NAME = "xgboost_fare_v1"
FARE_DEFAULT_DAY_OF_WEEK = 2  # Wednesday; see module docstring ponytail note

_demand_model: xgb.XGBRegressor | None = None
_fare_model: xgb.XGBRegressor | None = None
_zone_momentum: dict[int, dict[str, float]] = {}
_fare_categories: dict[str, list[int]] = {}
_zone_centroids: dict[int, tuple[float, float]] = {}


def load() -> None:
    """Load all artifacts once. Call this from FastAPI's startup hook."""
    global _demand_model, _fare_model

    print("[startup] Loading demand XGBoost model...", flush=True)
    _demand_model = xgb.XGBRegressor()
    _demand_model._estimator_type = "regressor"
    _demand_model.load_model(str(DEMAND_MODEL_PATH))

    print("[startup] Loading fare XGBoost model...", flush=True)
    _fare_model = xgb.XGBRegressor(enable_categorical=True)
    _fare_model._estimator_type = "regressor"
    _fare_model.load_model(str(FARE_MODEL_PATH))

    print(f"[startup] Connecting to DuckDB warehouse at {WAREHOUSE_PATH}...", flush=True)
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        print("[startup] Loading zone momentum features...", flush=True)
        _load_zone_momentum(con)
        print("[startup] Loading fare categories...", flush=True)
        _load_fare_categories(con)
    finally:
        con.close()

    print("[startup] Loading zone centroids...", flush=True)
    _load_zone_centroids()
    print("[startup] All artifacts loaded successfully!", flush=True)


def _load_zone_momentum(con: duckdb.DuckDBPyConnection) -> None:
    df = build_features(con)
    latest = df.sort_values("ts").groupby("pickup_location_id").tail(1)
    _zone_momentum.clear()
    for row in latest.itertuples():
        _zone_momentum[int(row.pickup_location_id)] = {
            "lag_1h": float(row.lag_1h),
            "lag_24h": float(row.lag_24h),
            "lag_168h": float(row.lag_168h),
            "ewma": float(row.ewma),
            "rolling_7d_avg": float(row.rolling_7d_avg),
        }


def _load_fare_categories(con: duckdb.DuckDBPyConnection) -> None:
    _fare_categories.clear()
    for col in ("pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week"):
        series = con.execute(f"select distinct {col} from int_trips_enriched order by 1").df()[col]
        _fare_categories[col] = series


def _load_zone_centroids() -> None:
    _zone_centroids.clear()
    for point in load_zone_points():
        _zone_centroids[point.location_id] = (point.lat, point.lon)


def _haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def get_zone_momentum(zone_id: int) -> dict[str, float] | None:
    """Real historical demand-momentum features (lag/EWMA/rolling-avg) for a
    zone, loaded once at startup by _load_zone_momentum(). Used by journey
    predictors (availability/surge/congestion) that need a real demand
    signal without invoking the trained model itself."""
    return _zone_momentum.get(zone_id)


def get_zone_centroid(zone_id: int) -> tuple[float, float] | None:
    return _zone_centroids.get(zone_id)


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    return _haversine_miles(a, b)


def predict_demand(zone_id: int, hour: int, day_of_week: int) -> tuple[float, str]:
    if _demand_model is None:
        raise RuntimeError("model_service.load() must run before predict_demand()")
    if zone_id not in _zone_momentum:
        raise KeyError(f"no demand history for zone_id={zone_id}")

    momentum = _zone_momentum[zone_id]
    row = {
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week in (5, 6)),
        **momentum,
    }
    features = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    pred = float(_demand_model.predict(features)[0])
    if pred > 0:
        return pred, DEMAND_MODEL_NAME
    # XGBoost has no non-negativity constraint and can extrapolate negative
    # for low-volume zones (their frozen momentum snapshot sits at the edge
    # of what the model saw in training). A flat 0 across every hour reads
    # as broken; fall back to the zone's own EWMA estimate instead -- it's
    # already computed, already part of the model ladder, and honestly
    # labeled via the returned model name rather than passed off as XGBoost.
    return momentum["ewma"], EWMA_FALLBACK_NAME


def predict_fare(pickup_zone: int, dropoff_zone: int, hour: int) -> tuple[float, str]:
    if _fare_model is None:
        raise RuntimeError("model_service.load() must run before predict_fare()")
    checks = (
        ("pickup_zone", pickup_zone, "pickup_location_id"),
        ("dropoff_zone", dropoff_zone, "dropoff_location_id"),
    )
    for name, zone_id, category_col in checks:
        if zone_id not in _zone_centroids or zone_id not in _fare_categories[category_col].values:
            raise KeyError(f"unknown {name}={zone_id}")

    trip_distance = _haversine_miles(_zone_centroids[pickup_zone], _zone_centroids[dropoff_zone])
    row = pd.DataFrame(
        [
            {
                "pickup_location_id": pickup_zone,
                "dropoff_location_id": dropoff_zone,
                "pickup_hour": hour,
                "pickup_day_of_week": FARE_DEFAULT_DAY_OF_WEEK,
                "trip_distance": trip_distance,
            }
        ]
    )
    for col in ("pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week"):
        row[col] = pd.Categorical(row[col], categories=_fare_categories[col])
    pred = float(_fare_model.predict(row)[0])
    return max(pred, 0.0), FARE_MODEL_NAME
