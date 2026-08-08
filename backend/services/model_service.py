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
from data_prep.build_features import FEATURE_COLUMNS as NYC_FEATURE_COLUMNS  # noqa: E402
from data_prep.build_features import build_features as nyc_build_features  # noqa: E402
from london_demand.build_features import FEATURE_COLUMNS as LONDON_FEATURE_COLUMNS  # noqa: E402
from london_demand.build_features import build_features as london_build_features  # noqa: E402

FARE_MODEL_PATH = REPO_ROOT / "models" / "fare_prediction" / "fare_xgb_model.json"
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

EWMA_FALLBACK_NAME = "ewma_fallback_v1"
FARE_MODEL_NAME = "xgboost_fare_v1"
FARE_DEFAULT_DAY_OF_WEEK = 2  # Wednesday; see module docstring ponytail note

# Per-city demand-model artifacts. Fare stays NYC-only below (no other city
# has a trained fare model) rather than genericizing a dict for one populated
# key -- see model_registry.csv, which has no london/fare row.
_CITY_ARTIFACTS: dict[str, dict] = {
    "nyc": {
        "demand_model_path": REPO_ROOT / "models" / "xgboost_model" / "xgb_model.json",
        "warehouse_path": WAREHOUSE_PATH,
        "build_features": nyc_build_features,
        "feature_columns": NYC_FEATURE_COLUMNS,
        "area_column": "pickup_location_id",
        "demand_model_name": "xgboost_demand_v1",
        "ewma_fallback_name": EWMA_FALLBACK_NAME,
    },
    "london": {
        "demand_model_path": REPO_ROOT / "models" / "london_demand" / "xgb_model.json",
        "warehouse_path": REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb",
        "build_features": london_build_features,
        "feature_columns": LONDON_FEATURE_COLUMNS,
        "area_column": "station_id",
        "demand_model_name": "xgboost_london_demand_v1",
        "ewma_fallback_name": EWMA_FALLBACK_NAME,
    },
}

_demand_models: dict[str, xgb.XGBRegressor] = {}
_fare_model: xgb.XGBRegressor | None = None
_zone_momentum: dict[str, dict[int, dict[str, float]]] = {}  # city_id -> area_id -> momentum
_fare_categories: dict[str, list[int]] = {}
_zone_centroids: dict[int, tuple[float, float]] = {}


def load() -> None:
    """Load all artifacts once. Call this from FastAPI's startup hook."""
    global _fare_model

    print("[startup] Loading per-city demand XGBoost models...", flush=True)
    _demand_models.clear()
    _zone_momentum.clear()
    for city_id, cfg in _CITY_ARTIFACTS.items():
        model = xgb.XGBRegressor()
        model._estimator_type = "regressor"
        model.load_model(str(cfg["demand_model_path"]))
        _demand_models[city_id] = model

        con = duckdb.connect(str(cfg["warehouse_path"]), read_only=True)
        try:
            _load_zone_momentum(con, city_id, cfg)
        finally:
            con.close()

    print("[startup] Loading fare XGBoost model...", flush=True)
    _fare_model = xgb.XGBRegressor(enable_categorical=True)
    _fare_model._estimator_type = "regressor"
    _fare_model.load_model(str(FARE_MODEL_PATH))

    print(f"[startup] Connecting to DuckDB warehouse at {WAREHOUSE_PATH}...", flush=True)
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        print("[startup] Loading fare categories...", flush=True)
        _load_fare_categories(con)
    finally:
        con.close()

    print("[startup] Loading zone centroids...", flush=True)
    _load_zone_centroids()
    print("[startup] All artifacts loaded successfully!", flush=True)


def _load_zone_momentum(con: duckdb.DuckDBPyConnection, city_id: str, cfg: dict) -> None:
    df = cfg["build_features"](con)
    area_column = cfg["area_column"]
    latest = df.sort_values("ts").groupby(area_column).tail(1)
    momentum: dict[int, dict[str, float]] = {}
    for row in latest.itertuples():
        momentum[int(getattr(row, area_column))] = {
            "lag_1h": float(row.lag_1h),
            "lag_24h": float(row.lag_24h),
            "lag_168h": float(row.lag_168h),
            "ewma": float(row.ewma),
            "rolling_7d_avg": float(row.rolling_7d_avg),
            # Last known real weather reading (city-level, from the same
            # frozen-snapshot discipline the lag features already use) -- the
            # model is trained on real historical weather, so inference needs
            # a real value here too, not a silent NaN every time.
            "temperature_c": float(row.temperature_c) if row.temperature_c == row.temperature_c else None,
            "precipitation_mm": float(row.precipitation_mm) if row.precipitation_mm == row.precipitation_mm else None,
        }
    _zone_momentum[city_id] = momentum


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


def get_zone_momentum(zone_id: int, city_id: str = "nyc") -> dict[str, float] | None:
    """Real historical demand-momentum features (lag/EWMA/rolling-avg) for a
    zone, loaded once at startup by _load_zone_momentum(). Used by journey
    predictors (availability/surge/congestion) that need a real demand
    signal without invoking the trained model itself."""
    return _zone_momentum.get(city_id, {}).get(zone_id)


def get_zone_centroid(zone_id: int) -> tuple[float, float] | None:
    return _zone_centroids.get(zone_id)


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    return _haversine_miles(a, b)


def predict_demand(zone_id: int, hour: int, day_of_week: int, city_id: str = "nyc") -> tuple[float, str]:
    if city_id not in _demand_models:
        raise KeyError(f"no demand model loaded for city_id={city_id!r}")
    momentum_by_area = _zone_momentum.get(city_id, {})
    if zone_id not in momentum_by_area:
        raise KeyError(f"no demand history for city_id={city_id!r} zone_id={zone_id}")

    cfg = _CITY_ARTIFACTS[city_id]
    momentum = momentum_by_area[zone_id]
    row = {
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week in (5, 6)),
        **momentum,
    }
    features = pd.DataFrame([row], columns=cfg["feature_columns"])
    pred = float(_demand_models[city_id].predict(features)[0])
    if pred > 0:
        return pred, cfg["demand_model_name"]
    # XGBoost has no non-negativity constraint and can extrapolate negative
    # for low-volume zones (their frozen momentum snapshot sits at the edge
    # of what the model saw in training). A flat 0 across every hour reads
    # as broken; fall back to the zone's own EWMA estimate instead -- it's
    # already computed, already part of the model ladder, and honestly
    # labeled via the returned model name rather than passed off as XGBoost.
    return momentum["ewma"], cfg["ewma_fallback_name"]


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
