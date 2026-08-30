"""GET /models/demand, /models/congestion, /models/fare, /models/eta,
POST /models/demand/lstm, /models/demand/transformer.

Raw-feature wrappers, one endpoint per trained model artifact in `models/`.
Distinct from `routers/predictions.py`'s `/predict/demand` and
`/predict/fare` (FR-2), which resolve their model features from zone
history/centroids automatically -- these take each model's exact training
features directly from the caller, matching `teerth_nyc_rides_ai.py`'s
per-model interface (used as the correctness reference for feature ordering
only, not imported).
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from loguru import logger

from backend.errors import DomainError
from backend.schemas import (
    CongestionPrediction,
    DemandFeaturesPrediction,
    DemandSequencePrediction,
    DemandSequenceRequest,
    ErrorCode,
    EtaRangePrediction,
    FareFeaturesPrediction,
)
from backend.services import model_service

router = APIRouter(prefix="/models", tags=["models"])


@router.get(
    "/demand",
    response_model=DemandFeaturesPrediction,
    summary="Predict demand from raw model features",
    description="Same trained XGBoost demand model as `/predict/demand`, but takes the "
    "lag/EWMA/rolling features directly instead of resolving them from a zone_id's history.",
    responses={400: {"description": "no demand model loaded"}},
)
def predict_demand_features(
    hour: int = Query(..., ge=0, le=23),
    day_of_week: int = Query(..., ge=0, le=6, description="0=Monday .. 6=Sunday"),
    is_weekend: int = Query(..., ge=0, le=1),
    lag_1h: float = Query(...),
    lag_24h: float = Query(...),
    lag_168h: float = Query(...),
    ewma: float = Query(...),
    rolling_7d_avg: float = Query(...),
    temperature_c: float = Query(...),
    precipitation_mm: float = Query(...),
) -> DemandFeaturesPrediction:
    logger.info("GET /models/demand step=start hour={} day_of_week={}", hour, day_of_week)
    try:
        pred, model_name, test_rmse = model_service.predict_demand_raw(
            hour, day_of_week, is_weekend, lag_1h, lag_24h, lag_168h,
            ewma, rolling_7d_avg, temperature_c, precipitation_mm,
        )
    except KeyError as exc:
        logger.warning("GET /models/demand step=predict_demand_raw failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    logger.info("GET /models/demand step=done model={} predicted={}", model_name, pred)
    return DemandFeaturesPrediction(predicted_trips_per_hour=pred, model=model_name, test_rmse=test_rmse)


@router.get(
    "/congestion",
    response_model=CongestionPrediction,
    summary="Predict the congestion multiplier over free-flow travel time",
    responses={400: {"description": "no congestion model loaded"}},
)
def predict_congestion(
    trip_distance: float = Query(..., description="miles"),
    free_flow_duration_min: float = Query(...),
    hour: int = Query(..., ge=0, le=23),
    day_of_week: int = Query(..., ge=0, le=6, description="0=Monday .. 6=Sunday"),
    is_holiday: int = Query(..., ge=0, le=1),
    temperature_c: float = Query(...),
    precipitation_mm: float = Query(...),
    demand_index: float = Query(...),
) -> CongestionPrediction:
    logger.info("GET /models/congestion step=start hour={} day_of_week={}", hour, day_of_week)
    try:
        pred, model_name, test_rmse = model_service.predict_congestion(
            trip_distance, free_flow_duration_min, hour, day_of_week,
            is_holiday, temperature_c, precipitation_mm, demand_index,
        )
    except KeyError as exc:
        logger.warning("GET /models/congestion step=predict_congestion failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    logger.info("GET /models/congestion step=done model={} predicted={}", model_name, pred)
    return CongestionPrediction(predicted_multiplier=pred, model=model_name, test_rmse=test_rmse)


@router.get(
    "/fare",
    response_model=FareFeaturesPrediction,
    summary="Predict fare from raw model features",
    description="Same trained XGBoost fare model as `/predict/fare`, but takes trip_distance "
    "directly instead of deriving it from pickup/dropoff zone centroids.",
    responses={400: {"description": "no fare model loaded, or pickup/dropoff location_id is unknown"}},
)
def predict_fare_features(
    pickup_location_id: int = Query(..., description="TLC LocationID"),
    dropoff_location_id: int = Query(..., description="TLC LocationID"),
    pickup_hour: int = Query(..., ge=0, le=23),
    pickup_day_of_week: int = Query(..., ge=0, le=6, description="0=Monday .. 6=Sunday"),
    trip_distance: float = Query(..., description="miles"),
) -> FareFeaturesPrediction:
    logger.info(
        "GET /models/fare step=start pickup_location_id={} dropoff_location_id={}",
        pickup_location_id, dropoff_location_id,
    )
    try:
        pred, model_name, test_rmse = model_service.predict_fare_raw(
            pickup_location_id, dropoff_location_id, pickup_hour, pickup_day_of_week, trip_distance,
        )
    except KeyError as exc:
        logger.warning("GET /models/fare step=predict_fare_raw failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    logger.info("GET /models/fare step=done model={} predicted={}", model_name, pred)
    return FareFeaturesPrediction(predicted_fare=pred, model=model_name, test_rmse=test_rmse)


@router.get(
    "/eta",
    response_model=EtaRangePrediction,
    summary="Predict a p10/p50/p90 ETA range",
    description="Three quantile XGBoost boosters over the same features as `/models/congestion`. "
    "`measured_p10_p90_coverage` on the response is the real measured calibration, not assumed; "
    "check it before trusting the range.",
    responses={400: {"description": "no eta model loaded"}},
)
def predict_eta(
    trip_distance: float = Query(..., description="miles"),
    free_flow_duration_min: float = Query(...),
    hour: int = Query(..., ge=0, le=23),
    day_of_week: int = Query(..., ge=0, le=6, description="0=Monday .. 6=Sunday"),
    is_holiday: int = Query(..., ge=0, le=1),
    temperature_c: float = Query(...),
    precipitation_mm: float = Query(...),
    demand_index: float = Query(...),
) -> EtaRangePrediction:
    logger.info("GET /models/eta step=start hour={} day_of_week={}", hour, day_of_week)
    try:
        p10, p50, p90, model_name, coverage = model_service.predict_eta_range(
            trip_distance, free_flow_duration_min, hour, day_of_week,
            is_holiday, temperature_c, precipitation_mm, demand_index,
        )
    except KeyError as exc:
        logger.warning("GET /models/eta step=predict_eta_range failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    logger.info("GET /models/eta step=done model={} p10={} p50={} p90={}", model_name, p10, p50, p90)
    return EtaRangePrediction(
        eta_p10_minutes=p10, eta_p50_minutes=p50, eta_p90_minutes=p90,
        model=model_name, measured_p10_p90_coverage=coverage,
    )


@router.post(
    "/demand/lstm",
    response_model=DemandSequencePrediction,
    summary="Predict next-hour demand from the last 24 hourly counts (LSTM)",
    responses={400: {"description": "no lstm model loaded, or hourly_trip_counts is the wrong length"}},
)
def predict_demand_lstm(req: DemandSequenceRequest) -> DemandSequencePrediction:
    logger.info("POST /models/demand/lstm step=start n={}", len(req.hourly_trip_counts))
    try:
        pred, model_name, test_rmse = model_service.predict_demand_lstm(req.hourly_trip_counts)
    except KeyError as exc:
        logger.warning("POST /models/demand/lstm step=predict_demand_lstm failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    except ValueError as exc:
        logger.warning("POST /models/demand/lstm step=predict_demand_lstm bad_input reason={}", exc)
        raise DomainError(ErrorCode.INVALID_REQUEST, str(exc), 400) from exc
    logger.info("POST /models/demand/lstm step=done model={} predicted={}", model_name, pred)
    return DemandSequencePrediction(predicted_next_hour_trips=pred, model=model_name, test_rmse=test_rmse)


@router.post(
    "/demand/transformer",
    response_model=DemandSequencePrediction,
    summary="Predict next-hour demand from the last 24 hourly counts (Transformer)",
    description="Same task/input shape as `/models/demand/lstm`, a different architecture -- kept "
    "as a separate endpoint deliberately so the two can be compared side by side on the same request.",
    responses={400: {"description": "no transformer model loaded, or hourly_trip_counts is the wrong length"}},
)
def predict_demand_transformer(req: DemandSequenceRequest) -> DemandSequencePrediction:
    logger.info("POST /models/demand/transformer step=start n={}", len(req.hourly_trip_counts))
    try:
        pred, model_name, test_rmse = model_service.predict_demand_transformer(req.hourly_trip_counts)
    except KeyError as exc:
        logger.warning("POST /models/demand/transformer step=predict_demand_transformer failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    except ValueError as exc:
        logger.warning("POST /models/demand/transformer step=predict_demand_transformer bad_input reason={}", exc)
        raise DomainError(ErrorCode.INVALID_REQUEST, str(exc), 400) from exc
    logger.info("POST /models/demand/transformer step=done model={} predicted={}", model_name, pred)
    return DemandSequencePrediction(predicted_next_hour_trips=pred, model=model_name, test_rmse=test_rmse)
