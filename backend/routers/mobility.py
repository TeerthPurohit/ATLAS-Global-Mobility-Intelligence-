"""Granular Mobility APIs (Part 2 of API Decomposition).

Each endpoint exposes one prediction component independently so the frontend
can load cards progressively, cache expensive results, and handle partial
failures. All endpoints share JourneyContextRequest for consistent inputs.

Internal: delegates to journey_service / pricing_engine / journey_predictors
so there is ONE source of truth per prediction (journey/estimate calls the
same services).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

# Add repo root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.predictors.base import PredictionResult  # noqa: E402
from backend.predictors import journey_predictors  # noqa: E402
from backend.schemas import (  # noqa: E402
    AvailabilityResponse,
    CarbonResponse,
    CongestionResponse,
    DemandResponse,
    DepartureTimeResponse,
    FareBreakdown,
    FareResponse,
    MobilityResponse,
    PredictionRequest,
    RouteRequest,
    RouteResponse,
    SurgeResponse,
)
from backend.services import journey_service, pricing_engine, model_service  # noqa: E402

router = APIRouter(prefix="/api/mobility", tags=["Mobility"])


def _make_mobility_response(pr: PredictionResult) -> MobilityResponse:
    """Convert internal PredictionResult to public MobilityResponse.

    Categorical predictors (congestion/availability/surge) keep their bucket
    string as `PredictionResult.value` for the /journey/estimate surface
    (ADR-007 + rag narrative), but this granular surface's response model
    requires a numeric `value`. The predictor's real 0-1 `score` is emitted
    here and the bucket label is folded into `reason` so the category stays
    visible to the user -- one source of truth, two shapes.
    """
    if pr.score is not None:
        reason = f"category {pr.value}; {pr.reason}" if pr.reason else f"category {pr.value}"
        return MobilityResponse(
            value=pr.score,
            unit="score_0_to_1",
            status=pr.basis,  # basis -> status mapping
            method=pr.method or "unknown",
            source=pr.source,
            confidence=pr.confidence if pr.confidence is not None else (0.0 if pr.basis == "unavailable" else 0.5),
            reason=reason,
        )
    return MobilityResponse(
        value=pr.value,
        unit=pr.unit,
        status=pr.basis,  # basis -> status mapping
        method=pr.method or "unknown",
        source=pr.source,
        confidence=pr.confidence if pr.confidence is not None else (0.0 if pr.basis == "unavailable" else 0.5),
        reason=pr.reason,
    )


def _predict_route(req: RouteRequest) -> tuple[PredictionResult, PredictionResult]:
    """Shared route prediction - returns (distance, duration)."""
    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)
    return features.distance_miles, features.duration_min


@router.post("/route", response_model=RouteResponse)
def route(req: RouteRequest) -> RouteResponse:
    """Get route distance and duration for a city.

    Uses OSRM with haversine fallback. Returns provenance for both fields.
    """
    request_id = str(uuid.uuid4())[:8]
    distance, duration = _predict_route(req)

    return RouteResponse(
        distance=_make_mobility_response(distance),
        duration=_make_mobility_response(duration),
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/fare", response_model=FareResponse)
def fare(req: PredictionRequest) -> FareResponse:
    """Get fare estimate for a journey.

    Uses trained model (NYC) or tariff profile (other cities).
    Optionally accepts pre-computed route to avoid recomputation.
    """
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )

    # Use provided route or compute
    if req.distance_km is not None and req.duration_min is not None:
        # Client-supplied route: distance/duration come from the request; the
        # historical traffic leg has nothing to score against (a zone pair
        # would need a fresh route resolution), so it is honestly
        # `unavailable` rather than a phantom attribute lookup.
        traffic_unavailable = PredictionResult(
            value=None, unit=None, basis="unavailable", source="historical_traffic_score",
            reason="route provided by client -- no zone-pair traffic score resolved",
        )
        from backend.predictors.base import JourneyFeatures
        features = JourneyFeatures(
            distance_miles=PredictionResult(
                value=req.distance_km / 1.609344, unit="miles", basis="computed", source="provided"
            ),
            duration_min=PredictionResult(
                value=req.duration_min, unit="minutes", basis="computed", source="provided"
            ),
            weather_score=ctx.weather,
            holiday_score=ctx.holiday,
            historical_traffic_score=traffic_unavailable,
            vehicle_profile=ctx.vehicle_profile,
        )
    else:
        features = journey_service.build_features(ctx)

    fare_terms = pricing_engine.compute_fare(ctx, features)
    total = fare_terms["total"]

    # FareBreakdown maps the pricing engine's named terms onto the response
    # fields -- labels are the public names, values are the real terms:
    #   base    <- base_fare           (trained model / tariff profile)
    #   distance<- vehicle_adjustment  (vehicle-class multiplier on base)
    #   duration<- traffic_adjustment  (historical-traffic surcharge)
    #   fees    <- weather_adjustment  (weather-severity surcharge)
    #   surge   <- demand_adjustment   (demand-momentum surcharge)
    breakdown = FareBreakdown(
        base=fare_terms.get("base_fare").value if fare_terms.get("base_fare") and fare_terms["base_fare"].value is not None else None,
        distance=fare_terms.get("vehicle_adjustment").value if fare_terms.get("vehicle_adjustment") and fare_terms["vehicle_adjustment"].value is not None else None,
        duration=fare_terms.get("traffic_adjustment").value if fare_terms.get("traffic_adjustment") and fare_terms["traffic_adjustment"].value is not None else None,
        fees=fare_terms.get("weather_adjustment").value if fare_terms.get("weather_adjustment") and fare_terms["weather_adjustment"].value is not None else None,
        surge=fare_terms.get("demand_adjustment").value if fare_terms.get("demand_adjustment") and fare_terms["demand_adjustment"].value is not None else None,
        total=total.value,
    )

    # Currency from base_fare term
    currency = total.unit

    return FareResponse(
        fare=_make_mobility_response(total),
        breakdown=breakdown,
        currency=currency,
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/demand", response_model=DemandResponse)
def demand(req: PredictionRequest) -> DemandResponse:
    """Get demand prediction for a pickup location and time."""
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)

    demand_result = journey_predictors.predict_demand(ctx, features)

    return DemandResponse(
        demand=_make_mobility_response(demand_result),
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/congestion", response_model=CongestionResponse)
def congestion(req: PredictionRequest) -> CongestionResponse:
    """Get congestion prediction for a journey."""
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)

    congestion_result = journey_predictors.predict_congestion(features)

    return CongestionResponse(
        congestion=_make_mobility_response(congestion_result),
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/availability", response_model=AvailabilityResponse)
def availability(req: PredictionRequest) -> AvailabilityResponse:
    """Get ride availability prediction."""
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)

    avail_result = journey_predictors.predict_availability(ctx, features)

    return AvailabilityResponse(
        availability=_make_mobility_response(avail_result),
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/surge", response_model=SurgeResponse)
def surge(req: PredictionRequest) -> SurgeResponse:
    """Get surge risk prediction.

    Separated from fare so surge is calculated exactly once and can be
    composed with base fare explicitly.
    """
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)

    surge_result = journey_predictors.predict_surge_risk(ctx, features)

    return SurgeResponse(
        surge=_make_mobility_response(surge_result),
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/carbon", response_model=CarbonResponse)
def carbon(req: PredictionRequest) -> CarbonResponse:
    """Get carbon emissions estimate."""
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)

    carbon_result = journey_predictors.predict_carbon(features)

    return CarbonResponse(
        carbon=_make_mobility_response(carbon_result),
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )


@router.post("/departure-time", response_model=DepartureTimeResponse)
def departure_time(req: PredictionRequest) -> DepartureTimeResponse:
    """Get recommended departure time."""
    request_id = str(uuid.uuid4())[:8]

    ctx = journey_service.build_context(
        req.pickup.lat, req.pickup.lon, req.dropoff.lat, req.dropoff.lon,
        req.departure_time, req.vehicle_type, req.city_id
    )
    features = journey_service.build_features(ctx)

    best = journey_predictors.sweep_best_departure_time(
        ctx.pickup_zone_id, req.departure_time.hour, req.departure_time.weekday(),
        window_hours=6, city_id=ctx.city_id,
    )

    return DepartureTimeResponse(
        recommended_departure=best.reason,  # reason contains the recommended time string
        reason=best.reason,
        confidence=best.confidence if best.confidence is not None else 0.0,
        status=best.basis,
        request_id=request_id,
        timestamp=datetime.utcnow(),
    )