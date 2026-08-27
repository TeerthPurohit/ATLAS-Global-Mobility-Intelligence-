"""POST /journey/estimate -- the Journey Intelligence Engine endpoint
(ADR-007). Thin: delegates to journey_service, maps PredictionResult ->
PredictionOut, appends the grounded AI recommendation from
rag/journey_narrative.py, and logs the request/response for future
training data (backend/services/prediction_log.py).

GET /journey/features is the feature inspector -- returns the same
JourneyFeatures a prediction would consume, without running any predictor,
for debugging "why did this predictor return X".
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rag import journey_narrative  # noqa: I001

from fastapi import APIRouter, Query
from loguru import logger

from backend.predictors.base import PredictionResult
from backend.schemas import JourneyEstimate, JourneyHistoryEntry, JourneyRequest, PredictionOut
from backend.services import journey_service, prediction_log

router = APIRouter(prefix="/journey", tags=["journey"])


def _to_out(pr: PredictionResult) -> PredictionOut:
    return PredictionOut(
        value=pr.value, unit=pr.unit, basis=pr.basis, source=pr.source, reason=pr.reason,
        data_vintage=pr.data_vintage, confidence=pr.confidence, method=pr.method,
    )


@router.post(
    "/estimate",
    response_model=JourneyEstimate,
    summary="Full journey estimate",
    description="The journey engine -- 11 signals (distance, duration, fare, "
    "fare_range, demand, carbon, congestion, availability, surge, best_departure_time, "
    "AI recommendation).",
)
def estimate(req: JourneyRequest) -> JourneyEstimate:
    logger.info("POST /journey/estimate step=start vehicle_type={}", req.vehicle_type)
    components = journey_service.estimate(
        pickup_lat=req.pickup_lat, pickup_lon=req.pickup_lon,
        dropoff_lat=req.dropoff_lat, dropoff_lon=req.dropoff_lon,
        departure_time=req.departure_time, vehicle_type=req.vehicle_type,
    )
    logger.info("POST /journey/estimate step=components_computed")
    text, basis = journey_narrative.generate(components)
    # basis is always "modeled_estimate" (grounded LLM/template prose) or
    # "unavailable" (not enough computed data) -- never "computed", since
    # prose is never a measured fact.
    reason = (
        "grounded narrative over the estimate's own numbers" if basis == "modeled_estimate"
        else "not enough computed data to narrate"
    )
    ai_recommendation = PredictionOut(value=text, unit=None, basis=basis, source="journey_narrative", reason=reason)

    fare_breakdown = {
        key.split("fare_breakdown.", 1)[1]: _to_out(value)
        for key, value in components.items()
        if key.startswith("fare_breakdown.")
    }

    result = JourneyEstimate(
        city_id=components["city_id"],
        distance=_to_out(components["distance"]),
        duration=_to_out(components["duration"]),
        fare=_to_out(components["fare"]),
        fare_range=_to_out(components["fare_range"]),
        demand=_to_out(components["demand"]),
        carbon_emissions=_to_out(components["carbon_emissions"]),
        congestion=_to_out(components["congestion"]),
        ride_availability=_to_out(components["ride_availability"]),
        surge_risk=_to_out(components["surge_risk"]),
        best_departure_time=_to_out(components["best_departure_time"]),
        confidence=_to_out(components["confidence"]),
        fare_breakdown=fare_breakdown,
        ai_recommendation=ai_recommendation,
    )
    logger.info("POST /journey/estimate step=logging_prediction")
    prediction_log.log_prediction(
        pickup_lat=req.pickup_lat, pickup_lon=req.pickup_lon,
        dropoff_lat=req.dropoff_lat, dropoff_lon=req.dropoff_lon,
        departure_time=req.departure_time.isoformat(), vehicle_type=req.vehicle_type,
        response=result.model_dump(),
    )
    logger.info("POST /journey/estimate step=done")
    return result


@router.get("/history", response_model=list[JourneyHistoryEntry])
def history(limit: int = Query(50, ge=1, le=200)) -> list[JourneyHistoryEntry]:
    logger.info("GET /journey/history step=start limit={}", limit)
    rows = [JourneyHistoryEntry(**row) for row in prediction_log.get_recent_predictions(limit=limit)]
    logger.info("GET /journey/history step=done count={}", len(rows))
    return rows


@router.get("/features")
def features(
    pickup_lat: float = Query(...), pickup_lon: float = Query(...),
    dropoff_lat: float = Query(...), dropoff_lon: float = Query(...),
    departure_time: datetime = Query(...), vehicle_type: str = Query(...),  # noqa: B008
    city_id: str | None = Query(None),
) -> dict:
    logger.info("GET /journey/features step=start city_id={} vehicle_type={}", city_id, vehicle_type)
    ctx = journey_service.build_context(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, departure_time, vehicle_type, city_id)
    features = journey_service.build_features(ctx)
    logger.info("GET /journey/features step=done city_id={}", ctx.city_id)
    return {
        "city_id": ctx.city_id,
        "pickup_zone_id": ctx.pickup_zone_id,
        "dropoff_zone_id": ctx.dropoff_zone_id,
        "vehicle_profile": features.vehicle_profile.__dict__ if features.vehicle_profile else None,
        "distance_miles": _to_out(features.distance_miles),
        "duration_min": _to_out(features.duration_min),
        "weather_score": _to_out(features.weather_score),
        "holiday_score": _to_out(features.holiday_score),
        "historical_traffic_score": _to_out(features.historical_traffic_score),
    }
