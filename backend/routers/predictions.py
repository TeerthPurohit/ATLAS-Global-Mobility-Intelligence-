"""GET /predict/demand, GET /predict/fare (FR-2). Thin: validates input,
delegates to model_service, maps lookup failures to 400."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.schemas import DemandPrediction, FarePrediction
from backend.services import model_service

router = APIRouter(prefix="/predict", tags=["predictions"])


@router.get(
    "/demand",
    response_model=DemandPrediction,
    summary="Predict pickup demand",
    description="Deprecated: superseded by `/api/cities/nyc/predict/demand` (identical NYC "
    "computation, plus it works for every other onboarded city). Kept for existing callers "
    "of this raw zone_id contract, not used by the frontend. Trained XGBoost demand model, "
    "honestly falling back to the zone's own EWMA estimate (relabeled in `model`) if the raw "
    "prediction extrapolates negative.",
    responses={400: {"description": "zone_id has no demand history"}},
    deprecated=True,
)
def predict_demand(
    zone_id: int = Query(..., description="TLC LocationID"),
    hour: int = Query(..., ge=0, le=23),
    day_of_week: int = Query(..., ge=0, le=6, description="0=Monday .. 6=Sunday"),
) -> DemandPrediction:
    logger.info("GET /predict/demand step=start zone_id={} hour={} day_of_week={}", zone_id, hour, day_of_week)
    try:
        predicted, model_name = model_service.predict_demand(zone_id, hour, day_of_week)
    except KeyError as exc:
        logger.warning("GET /predict/demand step=model_service.predict_demand failed zone_id={} reason={}", zone_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logger.info("GET /predict/demand step=done zone_id={} model={} predicted={}", zone_id, model_name, predicted)
    return DemandPrediction(
        zone_id=zone_id, hour=hour, day_of_week=day_of_week, predicted_demand=predicted, model=model_name
    )


@router.get(
    "/fare",
    response_model=FarePrediction,
    summary="Predict trip fare",
    description="Deprecated: superseded by `/api/cities/nyc/predict/fare` (identical NYC "
    "computation, plus it works for every other onboarded city). Kept for existing callers "
    "of this raw zone_id contract, not used by the frontend. Trained XGBoost fare model over "
    "a pickup/dropoff zone pair and hour.",
    responses={400: {"description": "pickup_zone or dropoff_zone is unknown"}},
    deprecated=True,
)
def predict_fare(
    pickup_zone: int = Query(..., description="TLC LocationID"),
    dropoff_zone: int = Query(..., description="TLC LocationID"),
    hour: int = Query(..., ge=0, le=23),
) -> FarePrediction:
    logger.info("GET /predict/fare step=start pickup_zone={} dropoff_zone={} hour={}", pickup_zone, dropoff_zone, hour)
    try:
        predicted, model_name = model_service.predict_fare(pickup_zone, dropoff_zone, hour)
    except KeyError as exc:
        logger.warning("GET /predict/fare step=model_service.predict_fare failed pickup_zone={} dropoff_zone={} reason={}", pickup_zone, dropoff_zone, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logger.info("GET /predict/fare step=done model={} predicted={}", model_name, predicted)
    return FarePrediction(
        pickup_zone=pickup_zone, dropoff_zone=dropoff_zone, hour=hour, predicted_fare=predicted, model=model_name
    )
