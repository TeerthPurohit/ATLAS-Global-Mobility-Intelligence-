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
# (city_id -> {(area_id, hour, day_of_week) -> feature dict}) -- the average
# historical lag/EWMA/rolling-avg profile for that exact (zone, hour,
# day-of-week) slot, not a single frozen snapshot. This is what makes
# predict_demand() actually respond to the requested hour/day rather than
# reusing 2024-06-30's last-known values for every query (the "stale
# numbers" bug -- see docs/superpowers/specs/2026-08-09-recovery-plan).
_zone_seasonal_profile: dict[str, dict[tuple[int, int, int], dict[str, float]]] = {}
# (city_id -> {(hour, day_of_week) -> fraction of that day-of-week's total
# volume falling in this hour, real SUM(total_trips) across every zone,
# sums to 1.0 across the 24 hours of a given day_of_week}). Used as a
# transferred prior to hourly-shape a population-scaled daily estimate for
# cities with no zone-level model of their own -- see
# estimation_service.estimate_hourly_demand().
_hourly_shape: dict[str, dict[tuple[int, int], float]] = {}
# (city_id -> {month -> multiplier}), a real SUM(total_trips)-weighted ratio
# of that month's average hourly volume to the city's overall average,
# clamped [0.5, 2.0] same convention as estimation_service's density/wet
# multipliers. Only months actually present in the warehouse get a
# non-neutral factor (see the Jan/Mar/Jun 2024 data-gap note in
# .claude/memory.md) -- an unmeasured month honestly falls back to 1.0.
_month_factor: dict[str, dict[int, float]] = {}
_MONTH_FACTOR_MIN, _MONTH_FACTOR_MAX = 0.5, 2.0
# (city_id -> "YYYY-MM-DD to YYYY-MM-DD") -- the real min/max date each
# city's mart covers, surfaced on every computed PredictionOut so nothing
# claims to be more current than it is.
_data_vintage: dict[str, str] = {}


def load() -> None:
    """Load all artifacts once. Call this from FastAPI's startup hook."""
    global _fare_model

    print("[startup] Loading per-city demand XGBoost models...", flush=True)
    _demand_models.clear()
    _zone_momentum.clear()
    _zone_seasonal_profile.clear()
    _month_factor.clear()
    _hourly_shape.clear()
    _data_vintage.clear()
    for city_id, cfg in _CITY_ARTIFACTS.items():
        model = xgb.XGBRegressor()
        model._estimator_type = "regressor"
        model.load_model(str(cfg["demand_model_path"]))
        _demand_models[city_id] = model

        con = duckdb.connect(str(cfg["warehouse_path"]), read_only=True)
        try:
            _load_zone_demand_artifacts(con, city_id, cfg)
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


_PROFILE_FEATURE_COLS = ("lag_1h", "lag_24h", "lag_168h", "ewma", "rolling_7d_avg", "temperature_c", "precipitation_mm")


def _load_zone_demand_artifacts(con: duckdb.DuckDBPyConnection, city_id: str, cfg: dict) -> None:
    """One `build_features()` pass feeds three artifacts: the last-known-row
    momentum snapshot (unchanged -- still what availability/surge/pricing's
    "current pressure" proxies read, since a precompute-only deployment with
    no live feed has no real notion of "now" past the warehouse's max date),
    the per-(zone, hour, day_of_week) seasonal profile predict_demand()
    actually predicts from, and a real month-of-year volume multiplier."""
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
            "temperature_c": float(row.temperature_c) if row.temperature_c == row.temperature_c else None,
            "precipitation_mm": float(row.precipitation_mm) if row.precipitation_mm == row.precipitation_mm else None,
        }
    _zone_momentum[city_id] = momentum

    profile: dict[tuple[int, int, int], dict[str, float]] = {}
    grouped = df.groupby([area_column, "hour", "day_of_week"])[list(_PROFILE_FEATURE_COLS)].mean()
    for (area_id, hour, dow), row in grouped.iterrows():
        profile[(int(area_id), int(hour), int(dow))] = {
            col: (float(row[col]) if row[col] == row[col] else None) for col in _PROFILE_FEATURE_COLS
        }
    _zone_seasonal_profile[city_id] = profile

    df = df.assign(month=df["ts"].dt.month)
    monthly_avg = df.groupby("month")["total_trips"].mean()
    overall_avg = df["total_trips"].mean()
    _month_factor[city_id] = {
        int(month): max(_MONTH_FACTOR_MIN, min(_MONTH_FACTOR_MAX, float(avg) / overall_avg))
        for month, avg in monthly_avg.items()
        if overall_avg > 0
    }

    _data_vintage[city_id] = f"{df['ts'].dt.date.min()} to {df['ts'].dt.date.max()}"

    volume_by_slot = df.groupby(["hour", "day_of_week"])["total_trips"].sum()
    volume_by_dow = df.groupby("day_of_week")["total_trips"].sum()
    _hourly_shape[city_id] = {
        (int(hour), int(dow)): float(vol) / float(volume_by_dow[dow])
        for (hour, dow), vol in volume_by_slot.items()
        if volume_by_dow.get(dow, 0) > 0
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


def get_zone_momentum(zone_id: int, city_id: str = "nyc") -> dict[str, float] | None:
    """Last-known-row demand-momentum snapshot for a zone, loaded once at
    startup. Used by journey predictors (availability/surge/pricing) as a
    "how does right now compare to this zone's own typical week" proxy --
    inherently a frozen fact for a precompute-only deployment with no live
    feed (rule 8: there is no real "now" past the warehouse's max date).
    Not used for predict_demand()'s hour/day-of-week-conditioned prediction
    -- see _zone_seasonal_profile for that."""
    return _zone_momentum.get(city_id, {}).get(zone_id)


def get_zone_centroid(zone_id: int) -> tuple[float, float] | None:
    return _zone_centroids.get(zone_id)


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    return _haversine_miles(a, b)


def hourly_shape_fraction(hour: int, day_of_week: int, city_id: str = "nyc") -> float | None:
    """Real fraction of `city_id`'s day_of_week total volume that falls in
    this hour (sums to 1.0 across a day_of_week's 24 hours). Falls back to a
    flat 1/24 only if this city has no loaded shape at all (never fabricates
    a curve for a city with real data but a missing slot)."""
    shape = _hourly_shape.get(city_id)
    if not shape:
        return None
    return shape.get((hour, day_of_week), 1.0 / 24.0)


def data_vintage(city_id: str) -> str | None:
    """Real min/max date range this city's demand mart actually covers --
    surfaced on every computed PredictionOut so nothing claims to be more
    current than a 2024/2026-dated warehouse actually is."""
    return _data_vintage.get(city_id)


def predict_demand(zone_id: int, hour: int, day_of_week: int, city_id: str = "nyc", month: int | None = None) -> tuple[float, str]:
    if city_id not in _demand_models:
        raise KeyError(f"no demand model loaded for city_id={city_id!r}")
    momentum_by_area = _zone_momentum.get(city_id, {})
    if zone_id not in momentum_by_area:
        raise KeyError(f"no demand history for city_id={city_id!r} zone_id={zone_id}")

    cfg = _CITY_ARTIFACTS[city_id]
    # The averaged (zone, hour, day_of_week) profile -- this is what makes
    # the requested time actually change the model's input, instead of every
    # query reusing one frozen last-known-row snapshot regardless of the
    # hour/day asked for. Falls back to that snapshot only if this exact
    # slot has zero historical rows (a low-volume zone's block-boundary gap).
    seasonal_features = _zone_seasonal_profile.get(city_id, {}).get((zone_id, hour, day_of_week))
    if seasonal_features is None:
        seasonal_features = momentum_by_area[zone_id]
    row = {
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week in (5, 6)),
        **seasonal_features,
    }
    features = pd.DataFrame([row], columns=cfg["feature_columns"])
    pred = float(_demand_models[city_id].predict(features)[0])
    if pred > 0:
        model_name = cfg["demand_model_name"]
    else:
        # XGBoost has no non-negativity constraint and can extrapolate
        # negative for low-volume zone/hour slots. A flat 0 reads as broken;
        # fall back to that slot's own EWMA estimate instead -- already
        # computed, already part of the model ladder, honestly labeled via
        # the returned model name rather than passed off as XGBoost.
        pred, model_name = seasonal_features["ewma"], cfg["ewma_fallback_name"]
    month_multiplier = _month_factor.get(city_id, {}).get(month, 1.0) if month is not None else 1.0
    return pred * month_multiplier, model_name


def predict_fare(pickup_zone: int, dropoff_zone: int, hour: int, day_of_week: int | None = None) -> tuple[float, str]:
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
                "pickup_day_of_week": day_of_week if day_of_week is not None else FARE_DEFAULT_DAY_OF_WEEK,
                "trip_distance": trip_distance,
            }
        ]
    )
    for col in ("pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week"):
        row[col] = pd.Categorical(row[col], categories=_fare_categories[col])
    pred = float(_fare_model.predict(row)[0])
    return max(pred, 0.0), FARE_MODEL_NAME
