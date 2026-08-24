"""Loads precomputed model artifacts once at startup (rule 8 — no training or
raw-table scans on a request path). Call `load()` from a FastAPI startup hook
before the app accepts traffic; routers call the `predict_*` functions only.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import duckdb
import pandas as pd
import xgboost as xgb
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from algorithms.spatial.kdtree_zone_lookup import load_zone_points  # noqa: E402
from data_prep.build_features import FEATURE_COLUMNS as NYC_FEATURE_COLUMNS  # noqa: E402
from data_prep.build_features import build_features as nyc_build_features  # noqa: E402

FARE_MODEL_PATH = REPO_ROOT / "models" / "fare_prediction" / "fare_xgb_model.json"

_FARE_CATEGORY_ORDER = ("pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week")
_FARE_CATEGORY_DTYPES = {
    "pickup_location_id": "int32",
    "dropoff_location_id": "int32",
    "pickup_hour": "int64",
    "pickup_day_of_week": "int64",
}
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

EWMA_FALLBACK_NAME = "ewma_fallback_v1"
FARE_MODEL_NAME = "xgboost_fare_v1"
FARE_DEFAULT_DAY_OF_WEEK = 2  # Wednesday; see module docstring ponytail note

# Demand-model artifacts (ADR-013: one city, so these are constants rather
# than a one-key dict keyed by a value that can only ever be "nyc").
DEMAND_MODEL_PATH = REPO_ROOT / "models" / "xgboost_model" / "xgb_model.json"
DEMAND_MODEL_NAME = "xgboost_demand_v1"
DEMAND_AREA_COLUMN = "pickup_location_id"
DEMAND_FEATURE_COLUMNS = NYC_FEATURE_COLUMNS
_build_demand_features = nyc_build_features

_demand_model: xgb.XGBRegressor | None = None
_fare_model: xgb.XGBRegressor | None = None
_zone_momentum: dict[int, dict[str, float]] = {}  # area_id -> momentum
_fare_categories: dict[str, list[int]] = {}
_zone_centroids: dict[int, tuple[float, float]] = {}
# {(area_id, hour, day_of_week) -> feature dict} -- the average historical
# lag/EWMA/rolling-avg profile for that exact (zone, hour, day-of-week) slot,
# not a single frozen snapshot. This is what makes predict_demand() actually
# respond to the requested hour/day rather than reusing the last-known values
# for every query (the "stale numbers" bug -- see
# docs/superpowers/specs/2026-08-09-recovery-plan).
_zone_seasonal_profile: dict[tuple[int, int, int], dict[str, float]] = {}
# {(hour, day_of_week) -> fraction of that day-of-week total volume falling
# in this hour, real SUM(total_trips) across every zone, sums to 1.0 across
# the 24 hours of a given day_of_week}.
_hourly_shape: dict[tuple[int, int], float] = {}
# {month -> multiplier}, a real SUM(total_trips)-weighted ratio of that
# month average hourly volume to the overall average, clamped [0.5, 2.0].
# Only months actually present in the warehouse get a non-neutral factor
# (see the month-gap note in .claude/memory.md) -- an unmeasured month
# honestly falls back to 1.0.
_month_factor: dict[int, float] = {}
_MONTH_FACTOR_MIN, _MONTH_FACTOR_MAX = 0.5, 2.0
# "YYYY-MM-DD to YYYY-MM-DD" -- the real min/max date the demand mart
# actually covers, surfaced on every computed PredictionOut so nothing
# claims to be more current than it is.
_data_vintage: str | None = None


def load() -> None:
    """Load all artifacts once. Call this from FastAPI's startup hook."""
    global _fare_model, _demand_model, _data_vintage

    logger.info("model_service.load step=demand_model_start")
    _demand_model = None
    _zone_momentum.clear()
    _zone_seasonal_profile.clear()
    _month_factor.clear()
    _hourly_shape.clear()
    _data_vintage = None
    try:
        if DEMAND_MODEL_PATH.exists():
            model = xgb.XGBRegressor()
            model._estimator_type = "regressor"
            model.load_model(str(DEMAND_MODEL_PATH))
            _demand_model = model

        if WAREHOUSE_PATH.exists():
            con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
            try:
                _load_zone_demand_artifacts(con)
            finally:
                con.close()
    except Exception:
        logger.exception("model_service.load step=demand_model failed -- demand predict will report unavailable")

    logger.info("model_service.load step=fare_model_start path={}", FARE_MODEL_PATH)
    _fare_model = xgb.XGBRegressor(enable_categorical=True)
    _fare_model._estimator_type = "regressor"
    _fare_model.load_model(str(FARE_MODEL_PATH))

    logger.info("model_service.load step=fare_categories")
    _load_fare_categories()

    logger.info("model_service.load step=zone_centroids")
    _load_zone_centroids()

    logger.info("model_service.load step=done demand_model_loaded={} fare_model_loaded={}", _demand_model is not None, _fare_model is not None)


_PROFILE_FEATURE_COLS = ("lag_1h", "lag_24h", "lag_168h", "ewma", "rolling_7d_avg", "temperature_c", "precipitation_mm")


def _load_zone_demand_artifacts(con: duckdb.DuckDBPyConnection) -> None:
    """One `build_features()` pass feeds three artifacts: momentum snapshot,
    seasonal profiles, and volume multipliers."""
    global _data_vintage
    df = _build_demand_features(con)
    area_column = DEMAND_AREA_COLUMN

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
    _zone_momentum.clear()
    _zone_momentum.update(momentum)

    profile: dict[tuple[int, int, int], dict[str, float]] = {}
    grouped = df.groupby([area_column, "hour", "day_of_week"])[list(_PROFILE_FEATURE_COLS)].mean()
    for (area_id, hour, dow), row in grouped.iterrows():
        profile[(int(area_id), int(hour), int(dow))] = {
            col: (float(row[col]) if row[col] == row[col] else None) for col in _PROFILE_FEATURE_COLS
        }
    _zone_seasonal_profile.clear()
    _zone_seasonal_profile.update(profile)

    df = df.assign(month=df["ts"].dt.month)
    monthly_avg = df.groupby("month")["total_trips"].mean()
    overall_avg = df["total_trips"].mean()
    _month_factor.clear()
    _month_factor.update({
        int(month): max(_MONTH_FACTOR_MIN, min(_MONTH_FACTOR_MAX, float(avg) / overall_avg))
        for month, avg in monthly_avg.items()
        if overall_avg > 0
    })

    _data_vintage = f"{df['ts'].dt.date.min()} to {df['ts'].dt.date.max()}"

    volume_by_slot = df.groupby(["hour", "day_of_week"])["total_trips"].sum()
    volume_by_dow = df.groupby("day_of_week")["total_trips"].sum()
    _hourly_shape.clear()
    _hourly_shape.update({
        (int(hour), int(dow)): float(vol) / float(volume_by_dow[dow])
        for (hour, dow), vol in volume_by_slot.items()
        if volume_by_dow.get(dow, 0) > 0
    })


def _load_fare_categories() -> None:
    """Build the categorical feature encodings the fare model expects.

    Must match training EXACTLY: XGBoost's enable_categorical path rejects a
    categorical index dtype mismatch AND any category value that wasn't in the
    training set. The faithful source is the model file itself -- it stores the
    training category values per feature under
    `learner.gradient_booster.model.cats.enc` -- so no slow distinct-value
    scan over the 113M-row warehouse is needed.

    Dtypes mirror what `fetchdf()` returned at train time per warehouse column
    type: zone ids are INTEGER (numpy int32), hour/day_of_week are BIGINT
    (numpy int64). Feeding the exact stored values with the matching dtype is
    what makes the trained model accept a row.
    """
    _fare_categories.clear()
    model_doc = json.loads(Path(FARE_MODEL_PATH).read_text(encoding="utf-8"))
    enc = model_doc["learner"]["gradient_booster"]["model"]["cats"]["enc"]
    for col, entry in zip(_FARE_CATEGORY_ORDER, enc):
        _fare_categories[col] = pd.Series(entry["values"], dtype=_FARE_CATEGORY_DTYPES[col])


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
    """Last-known-row demand-momentum snapshot for a zone, loaded once at
    startup. Used by journey predictors (availability/surge/pricing) as a
    "how does right now compare to this zone's own typical week" proxy --
    inherently a frozen fact for a precompute-only deployment with no live
    feed (rule 8: there is no real "now" past the warehouse's max date).
    Not used for predict_demand()'s hour/day-of-week-conditioned prediction
    -- see _zone_seasonal_profile for that."""
    return _zone_momentum.get(zone_id)


def get_zone_centroid(zone_id: int) -> tuple[float, float] | None:
    return _zone_centroids.get(zone_id)


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    return _haversine_miles(a, b)


def hourly_shape_fraction(hour: int, day_of_week: int) -> float | None:
    """Real fraction of the day_of_week total volume that falls in this hour
    (sums to 1.0 across a day_of_week 24 hours). Returns None only if no
    shape is loaded at all (never fabricates a curve for a slot that has real
    data behind the rest of its day)."""
    if not _hourly_shape:
        return None
    return _hourly_shape.get((hour, day_of_week), 1.0 / 24.0)


def data_vintage() -> str | None:
    """Real min/max date range the demand mart actually covers -- surfaced on
    every computed PredictionOut so nothing claims to be more current than a
    2024/2026-dated warehouse actually is."""
    return _data_vintage


def predict_demand(zone_id: int, hour: int, day_of_week: int, month: int | None = None) -> tuple[float, str]:
    if _demand_model is None:
        logger.debug("model_service.predict_demand step=no_model_loaded")
        raise KeyError("no demand model loaded")
    if zone_id not in _zone_momentum:
        logger.debug("model_service.predict_demand step=no_history zone_id={}", zone_id)
        raise KeyError(f"no demand history for zone_id={zone_id}")
    # The averaged (zone, hour, day_of_week) profile -- this is what makes
    # the requested time actually change the model's input, instead of every
    # query reusing one frozen last-known-row snapshot regardless of the
    # hour/day asked for. Falls back to that snapshot only if this exact
    # slot has zero historical rows (a low-volume zone's block-boundary gap).
    seasonal_features = _zone_seasonal_profile.get((zone_id, hour, day_of_week))
    if seasonal_features is None:
        seasonal_features = _zone_momentum[zone_id]
    row = {
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week in (5, 6)),
        **seasonal_features,
    }
    features = pd.DataFrame([row], columns=DEMAND_FEATURE_COLUMNS)
    pred = float(_demand_model.predict(features)[0])
    if pred > 0:
        model_name = DEMAND_MODEL_NAME
    else:
        # XGBoost has no non-negativity constraint and can extrapolate
        # negative for low-volume zone/hour slots. A flat 0 reads as broken;
        # fall back to that slot's own EWMA estimate instead -- already
        # computed, already part of the model ladder, honestly labeled via
        # the returned model name rather than passed off as XGBoost.
        pred, model_name = seasonal_features["ewma"], EWMA_FALLBACK_NAME
    month_multiplier = _month_factor.get(month, 1.0) if month is not None else 1.0
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
    for col in _FARE_CATEGORY_ORDER:
        # Cast to the category dtype first so the Categorical index dtype
        # (int32 for zones, int64 for hour/dow) matches training, then apply
        # the model's exact stored training categories.
        row[col] = pd.Categorical(row[col].astype(_FARE_CATEGORY_DTYPES[col]), categories=_fare_categories[col])
    pred = float(_fare_model.predict(row)[0])
    return max(pred, 0.0), FARE_MODEL_NAME
