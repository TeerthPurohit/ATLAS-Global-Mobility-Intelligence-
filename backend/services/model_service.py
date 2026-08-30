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
import numpy as np
import pandas as pd
import torch
import xgboost as xgb
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from algorithms.spatial.kdtree_zone_lookup import load_zone_points  # noqa: E402, I001
from data_prep.build_features import FEATURE_COLUMNS as NYC_FEATURE_COLUMNS  # noqa: E402
from data_prep.build_features import build_features as nyc_build_features  # noqa: E402
from models.lstm_model.train_lstm import DemandLSTM  # noqa: E402
from models.transformer_demand.transformer import DemandTransformer  # noqa: E402

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
DEMAND_METADATA_PATH = REPO_ROOT / "models" / "xgboost_model" / "xgb_metadata.json"
DEMAND_MODEL_NAME = "xgboost_demand_v1"
DEMAND_AREA_COLUMN = "pickup_location_id"
DEMAND_FEATURE_COLUMNS = NYC_FEATURE_COLUMNS
_build_demand_features = nyc_build_features
FARE_METADATA_PATH = REPO_ROOT / "models" / "fare_prediction" / "fare_xgb_metadata.json"

# Congestion-multiplier and quantile-ETA artifacts (both plain xgb.Booster --
# trained via the streaming/external-memory path, not the sklearn wrapper --
# so they're loaded and predicted through Booster/DMatrix directly, same as
# `teerth_nyc_rides_ai.py`'s reference implementation).
CONGESTION_MODEL_PATH = REPO_ROOT / "models" / "congestion" / "congestion_model.json"
CONGESTION_METADATA_PATH = REPO_ROOT / "models" / "congestion" / "congestion_metadata.json"
CONGESTION_MODEL_NAME = "xgboost_congestion_v1"

# eta_p10/p50/p90_model.json: retrained 2026-08-30 on the full 113M-row
# corpus via Kaggle GPU (see models/eta/eta_gpu_ladder_report.json) --
# measured p10-p90 coverage is 0.7946 vs nominal 0.8. This module loads and
# serves whatever files are on disk by path/plumbing only; it does not
# hardcode a correctness claim here, so no code change is needed if these
# files are retrained again -- check eta_metadata.json's
# prediction_interval_coverage for the current honest number.
ETA_P10_MODEL_PATH = REPO_ROOT / "models" / "eta" / "eta_p10_model.json"
ETA_P50_MODEL_PATH = REPO_ROOT / "models" / "eta" / "eta_p50_model.json"
ETA_P90_MODEL_PATH = REPO_ROOT / "models" / "eta" / "eta_p90_model.json"
ETA_METADATA_PATH = REPO_ROOT / "models" / "eta" / "eta_metadata.json"
ETA_MODEL_NAME = "xgboost_quantile_eta_v1"

LSTM_MODEL_PATH = REPO_ROOT / "models" / "lstm_model" / "lstm_model.pt"
LSTM_METADATA_PATH = REPO_ROOT / "models" / "lstm_model" / "lstm_metadata.json"
LSTM_MODEL_NAME = "lstm_demand_v1"

TRANSFORMER_MODEL_PATH = REPO_ROOT / "models" / "transformer_demand" / "transformer_model.pt"
TRANSFORMER_METADATA_PATH = REPO_ROOT / "models" / "transformer_demand" / "transformer_metadata.json"
TRANSFORMER_MODEL_NAME = "transformer_demand_v1"

_demand_model: xgb.XGBRegressor | None = None
_demand_meta: dict | None = None
_fare_model: xgb.XGBRegressor | None = None
_fare_meta: dict | None = None
_congestion_model: xgb.Booster | None = None
_congestion_meta: dict | None = None
_eta_p10: xgb.Booster | None = None
_eta_p50: xgb.Booster | None = None
_eta_p90: xgb.Booster | None = None
_eta_meta: dict | None = None
_lstm_model: DemandLSTM | None = None
_lstm_meta: dict | None = None
_transformer_model: DemandTransformer | None = None
_transformer_meta: dict | None = None
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
    global _fare_model, _fare_meta, _demand_model, _demand_meta, _data_vintage
    global _congestion_model, _congestion_meta, _eta_p10, _eta_p50, _eta_p90, _eta_meta
    global _lstm_model, _lstm_meta, _transformer_model, _transformer_meta

    logger.info("model_service.load step=demand_model_start")
    _demand_model = None
    _demand_meta = json.loads(DEMAND_METADATA_PATH.read_text(encoding="utf-8")) if DEMAND_METADATA_PATH.exists() else None
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
    except Exception:  # noqa: BLE001
        logger.exception("model_service.load step=demand_model failed -- demand predict will report unavailable")

    logger.info("model_service.load step=fare_model_start path={}", FARE_MODEL_PATH)
    _fare_model = xgb.XGBRegressor(enable_categorical=True)
    _fare_model._estimator_type = "regressor"
    _fare_model.load_model(str(FARE_MODEL_PATH))
    _fare_meta = json.loads(FARE_METADATA_PATH.read_text(encoding="utf-8")) if FARE_METADATA_PATH.exists() else None

    logger.info("model_service.load step=fare_categories")
    _load_fare_categories()

    logger.info("model_service.load step=zone_centroids")
    _load_zone_centroids()

    # Each of the four artifacts below is isolated in its own try/except:
    # one missing/corrupt file (e.g. the eta boosters, mid-fix by a parallel
    # task) disables only that capability, not demand/fare above.
    logger.info("model_service.load step=congestion_model_start")
    _congestion_model, _congestion_meta = None, None
    try:
        if CONGESTION_MODEL_PATH.exists():
            booster = xgb.Booster()
            booster.load_model(str(CONGESTION_MODEL_PATH))
            _congestion_model = booster
            _congestion_meta = json.loads(CONGESTION_METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("model_service.load step=congestion_model failed -- congestion predict will report unavailable")

    logger.info("model_service.load step=eta_model_start")
    _eta_p10, _eta_p50, _eta_p90, _eta_meta = None, None, None, None
    try:
        if ETA_P10_MODEL_PATH.exists() and ETA_P50_MODEL_PATH.exists() and ETA_P90_MODEL_PATH.exists():
            p10, p50, p90 = xgb.Booster(), xgb.Booster(), xgb.Booster()
            p10.load_model(str(ETA_P10_MODEL_PATH))
            p50.load_model(str(ETA_P50_MODEL_PATH))
            p90.load_model(str(ETA_P90_MODEL_PATH))
            _eta_p10, _eta_p50, _eta_p90 = p10, p50, p90
            _eta_meta = json.loads(ETA_METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("model_service.load step=eta_model failed -- eta predict will report unavailable")

    logger.info("model_service.load step=lstm_model_start")
    _lstm_model, _lstm_meta = None, None
    try:
        if LSTM_MODEL_PATH.exists():
            meta = json.loads(LSTM_METADATA_PATH.read_text(encoding="utf-8"))
            hp = meta["hyperparameters"]
            lstm = DemandLSTM(hidden_size=hp["hidden_size"], num_layers=hp["num_layers"])
            lstm.load_state_dict(torch.load(str(LSTM_MODEL_PATH), map_location="cpu"))
            lstm.eval()
            _lstm_model, _lstm_meta = lstm, meta
    except Exception:  # noqa: BLE001
        logger.exception("model_service.load step=lstm_model failed -- lstm predict will report unavailable")

    logger.info("model_service.load step=transformer_model_start")
    _transformer_model, _transformer_meta = None, None
    try:
        if TRANSFORMER_MODEL_PATH.exists():
            meta = json.loads(TRANSFORMER_METADATA_PATH.read_text(encoding="utf-8"))
            hp = meta["hyperparameters"]
            transformer = DemandTransformer(
                d_model=hp["d_model"], num_heads=hp["num_heads"], num_layers=hp["num_layers"],
                dim_feedforward=hp["dim_feedforward"], dropout=0.0,
            )
            transformer.load_state_dict(torch.load(str(TRANSFORMER_MODEL_PATH), map_location="cpu"))
            transformer.eval()
            _transformer_model, _transformer_meta = transformer, meta
    except Exception:  # noqa: BLE001
        logger.exception("model_service.load step=transformer_model failed -- transformer predict will report unavailable")

    logger.info(
        "model_service.load step=done demand_model_loaded={} fare_model_loaded={} congestion_model_loaded={} "
        "eta_model_loaded={} lstm_model_loaded={} transformer_model_loaded={}",
        _demand_model is not None, _fare_model is not None, _congestion_model is not None,
        _eta_p10 is not None, _lstm_model is not None, _transformer_model is not None,
    )


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
    row = _encode_fare_categoricals(row)
    pred = float(_fare_model.predict(row)[0])
    return max(pred, 0.0), FARE_MODEL_NAME


def _encode_fare_categoricals(row: pd.DataFrame) -> pd.DataFrame:
    """Shared by `predict_fare` and `predict_fare_raw` -- both call the same
    `_fare_model` artifact, which requires its exact training-time categorical
    encoding (see `_load_fare_categories` docstring) regardless of how
    `trip_distance` was obtained."""
    for col in _FARE_CATEGORY_ORDER:
        # Cast to the category dtype first so the Categorical index dtype
        # (int32 for zones, int64 for hour/dow) matches training, then apply
        # the model's exact stored training categories.
        row[col] = pd.Categorical(row[col].astype(_FARE_CATEGORY_DTYPES[col]), categories=_fare_categories[col])
    return row


def predict_fare_raw(
    pickup_location_id: int, dropoff_location_id: int, pickup_hour: int,
    pickup_day_of_week: int, trip_distance: float,
) -> tuple[float, str, float | None]:
    """Raw fare-model surface: caller supplies `trip_distance` directly
    (e.g. a known route distance) instead of `predict_fare`'s zone-centroid
    haversine convenience path. Same artifact (FARE_MODEL_PATH) and the same
    required categorical encoding as `predict_fare` -- see
    `_encode_fare_categoricals`."""
    if _fare_model is None:
        raise KeyError("no fare model loaded")
    checks = (
        ("pickup_location_id", pickup_location_id, "pickup_location_id"),
        ("dropoff_location_id", dropoff_location_id, "dropoff_location_id"),
    )
    for name, zone_id, category_col in checks:
        if zone_id not in _fare_categories.get(category_col, pd.Series(dtype="int64")).values:
            raise KeyError(f"unknown {name}={zone_id}")
    row = pd.DataFrame(
        [
            {
                "pickup_location_id": pickup_location_id,
                "dropoff_location_id": dropoff_location_id,
                "pickup_hour": pickup_hour,
                "pickup_day_of_week": pickup_day_of_week,
                "trip_distance": trip_distance,
            }
        ]
    )
    row = _encode_fare_categoricals(row)
    pred = float(_fare_model.predict(row)[0])
    test_rmse = _fare_meta["metrics"]["test_rmse"] if _fare_meta else None
    return max(pred, 0.0), FARE_MODEL_NAME, test_rmse


def predict_demand_raw(
    hour: int, day_of_week: int, is_weekend: int, lag_1h: float, lag_24h: float,
    lag_168h: float, ewma: float, rolling_7d_avg: float, temperature_c: float, precipitation_mm: float,
) -> tuple[float, str, float | None]:
    """Raw demand-model surface: caller supplies the exact lag/EWMA/rolling
    features `xgb_model.json` was trained on directly, instead of
    `predict_demand`'s zone_id/hour/day_of_week path that resolves them from
    warehouse history. Same underlying artifact as `predict_demand`."""
    if _demand_model is None:
        raise KeyError("no demand model loaded")
    row = {
        "hour": hour, "day_of_week": day_of_week, "is_weekend": is_weekend,
        "lag_1h": lag_1h, "lag_24h": lag_24h, "lag_168h": lag_168h, "ewma": ewma,
        "rolling_7d_avg": rolling_7d_avg, "temperature_c": temperature_c, "precipitation_mm": precipitation_mm,
    }
    features = pd.DataFrame([row], columns=DEMAND_FEATURE_COLUMNS)
    pred = float(_demand_model.predict(features)[0])
    test_rmse = _demand_meta["metrics"]["test_rmse"] if _demand_meta else None
    return pred, DEMAND_MODEL_NAME, test_rmse


def predict_congestion(
    trip_distance: float, free_flow_duration_min: float, hour: int, day_of_week: int,
    is_holiday: int, temperature_c: float, precipitation_mm: float, demand_index: float,
) -> tuple[float, str, float | None]:
    """Multiplier applied to free-flow travel time to get expected real
    duration (actual_duration ~= free_flow_duration_min * multiplier)."""
    if _congestion_model is None:
        raise KeyError("no congestion model loaded")
    row = {
        "trip_distance": trip_distance, "free_flow_duration_min": free_flow_duration_min,
        "hour": hour, "day_of_week": day_of_week, "is_holiday": is_holiday,
        "temperature_c": temperature_c, "precipitation_mm": precipitation_mm, "demand_index": demand_index,
    }
    cols = _congestion_meta["features"]
    dmat = xgb.DMatrix(pd.DataFrame([row], columns=cols))
    pred = float(_congestion_model.predict(dmat)[0])
    test_rmse = _congestion_meta["metrics"]["test_rmse"]
    return pred, CONGESTION_MODEL_NAME, test_rmse


def predict_eta_range(
    trip_distance: float, free_flow_duration_min: float, hour: int, day_of_week: int,
    is_holiday: int, temperature_c: float, precipitation_mm: float, demand_index: float,
) -> tuple[float, float, float, str, float | None]:
    """p10/p50/p90 trip-duration minutes from the three quantile ETA boosters.

    This function only loads whatever booster files exist at the paths above
    and returns their real predictions plus the real measured coverage
    number from `eta_metadata.json` -- if the models are retrained, no code
    here needs to change. As of the 2026-08-30 full-113M-row GPU retrain,
    measured p10-p90 coverage is 0.7946 vs nominal 0.8."""
    if _eta_p10 is None or _eta_p50 is None or _eta_p90 is None:
        raise KeyError("no eta model loaded")
    row = {
        "trip_distance": trip_distance, "free_flow_duration_min": free_flow_duration_min,
        "hour": hour, "day_of_week": day_of_week, "is_holiday": is_holiday,
        "temperature_c": temperature_c, "precipitation_mm": precipitation_mm, "demand_index": demand_index,
    }
    cols = _eta_meta["features"]
    dmat = xgb.DMatrix(pd.DataFrame([row], columns=cols))
    p10 = float(_eta_p10.predict(dmat)[0])
    p50 = float(_eta_p50.predict(dmat)[0])
    p90 = float(_eta_p90.predict(dmat)[0])
    coverage = _eta_meta.get("prediction_interval_coverage", {}).get("measured_p10_p90_coverage")
    return p10, p50, p90, ETA_MODEL_NAME, coverage


def predict_demand_lstm(hourly_trip_counts: list[float]) -> tuple[float, str, float | None]:
    """Next-hour zone demand from the last `window` (24) hourly trip counts
    (raw counts, not pre-normalized -- normalization uses the model's own
    stored train-set mean/std, `lstm_metadata.json`'s `target_scaling`)."""
    if _lstm_model is None or _lstm_meta is None:
        raise KeyError("no lstm model loaded")
    window = _lstm_meta["window"]
    if len(hourly_trip_counts) != window:
        raise ValueError(f"expected {window} hourly values, got {len(hourly_trip_counts)}")
    mean = _lstm_meta["target_scaling"]["mean"]
    std = _lstm_meta["target_scaling"]["std"]
    x = (np.array(hourly_trip_counts, dtype=np.float32) - mean) / std
    x = torch.from_numpy(x).reshape(1, -1, 1)
    with torch.no_grad():
        pred_norm = _lstm_model(x).item()
    pred = pred_norm * std + mean
    test_rmse = _lstm_meta["metrics"]["test_rmse"]
    return pred, LSTM_MODEL_NAME, test_rmse


def predict_demand_transformer(hourly_trip_counts: list[float]) -> tuple[float, str, float | None]:
    """Same task/window as `predict_demand_lstm`, a different architecture
    kept as a separate endpoint deliberately so the two can be compared
    side by side on the same request (see
    models/transformer_demand/comparison_report.md).

    `train_transformer.py` standardizes BOTH the input window and the target
    using the target's own train-set mean/std (`transformer_metadata.json`'s
    `target_scaling`) before the model ever sees a value, then
    inverse-transforms the prediction -- this mirrors that exactly. (The
    standalone `teerth_nyc_rides_ai.py` reference script skips this
    normalization step for the transformer, which would silently misscale
    every prediction; this function does not follow it there.)"""
    if _transformer_model is None or _transformer_meta is None:
        raise KeyError("no transformer model loaded")
    window = _transformer_meta["window"]
    if len(hourly_trip_counts) != window:
        raise ValueError(f"expected {window} hourly values, got {len(hourly_trip_counts)}")
    mean = _transformer_meta["target_scaling"]["mean"]
    std = _transformer_meta["target_scaling"]["std"]
    x = (np.array(hourly_trip_counts, dtype=np.float32) - mean) / std
    x = torch.from_numpy(x).reshape(1, -1, 1)
    with torch.no_grad():
        pred_norm = _transformer_model(x).item()
    pred = pred_norm * std + mean
    test_rmse = _transformer_meta["metrics"]["test_rmse"]
    return pred, TRANSFORMER_MODEL_NAME, test_rmse
