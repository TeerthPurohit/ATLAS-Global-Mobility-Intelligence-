"""GET /predict/demand, GET /predict/fare (FR-2). Thin: validates input,
delegates to model_service, maps lookup failures to 400."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.schemas import DemandPrediction, FarePrediction
from backend.services import model_service

router = APIRouter(prefix="/predict", tags=["predictions"])


@router.get("/demand", response_model=DemandPrediction)
def predict_demand(
    zone_id: int = Query(..., description="TLC LocationID"),
    hour: int = Query(..., ge=0, le=23),
    day_of_week: int = Query(..., ge=0, le=6, description="0=Monday .. 6=Sunday"),
) -> DemandPrediction:
    try:
        predicted, model_name = model_service.predict_demand(zone_id, hour, day_of_week)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DemandPrediction(
        zone_id=zone_id, hour=hour, day_of_week=day_of_week, predicted_demand=predicted, model=model_name
    )


@router.get("/fare", response_model=FarePrediction)
def predict_fare(
    pickup_zone: int = Query(..., description="TLC LocationID"),
    dropoff_zone: int = Query(..., description="TLC LocationID"),
    hour: int = Query(..., ge=0, le=23),
) -> FarePrediction:
    try:
        predicted, model_name = model_service.predict_fare(pickup_zone, dropoff_zone, hour)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FarePrediction(
        pickup_zone=pickup_zone, dropoff_zone=dropoff_zone, hour=hour, predicted_fare=predicted, model=model_name
    )
