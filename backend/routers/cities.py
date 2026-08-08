"""City discovery + city-scoped predict/chat routes (SPEC-013 FR-9). Thin:
delegates to backend/registry/{countries,cities}.py, backend/services/
geography_service.py, backend/services/prediction_service.py, and the
existing (unchanged) backend/services/rag_service.py. Every pre-existing
route (`/predict/demand`, `/predict/fare`, `/zones`, `/chat`,
`/journey/estimate`) stays mounted, unchanged, in backend/main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.errors import DomainError
from backend.registry import cities as cities_registry
from backend.registry import countries as countries_registry
from backend.schemas import (
    Area,
    CapabilityUnavailable,
    Capabilities,
    ChatRequest,
    ChatResponse,
    City,
    CityDemandPredictRequest,
    CityFarePredictRequest,
    CityJourneyEstimate,
    CityJourneyRequest,
    ErrorCode,
    ErrorResponse,
    ForecastEnvelope,
    PredictionEnvelope,
)
from backend.services import city_journey_service, geography_service, global_geography_service, prediction_service, rag_service

router = APIRouter(tags=["Cities"])


def _require_city(city_id: str) -> dict:
    city = cities_registry.get_city(city_id)
    if city is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return city


@router.get(
    "/api/countries/{code}/cities",
    response_model=list[City],
    summary="List a country's onboarded cities",
    tags=["Countries"],
    responses={404: {"model": ErrorResponse, "description": "Country not supported"}},
)
def list_country_cities(code: str) -> list[City]:
    country = countries_registry.get_country(code)
    if country is None or not country["supported"]:
        raise DomainError(ErrorCode.COUNTRY_NOT_SUPPORTED, f"country not supported: {code!r}", 404)
    return [City(**c) for c in cities_registry.list_cities(country_code=code)]


@router.get(
    "/api/cities/{city_id}",
    response_model=City,
    summary="Get a city",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def get_city(city_id: str) -> City:
    return City(**_require_city(city_id))


@router.get(
    "/api/cities/{city_id}/capabilities",
    response_model=Capabilities,
    summary="Get a city's real, wired capabilities",
    description="Never aspirational -- demand/fare/journey are true iff an active "
    "model_registry row backs them, area_analysis iff canonical_areas has rows for this city.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def get_capabilities(city_id: str) -> Capabilities:
    _require_city(city_id)
    return Capabilities(**cities_registry.get_capabilities(city_id))


@router.get(
    "/api/cities/{city_id}/areas",
    response_model=list[Area],
    summary="List a city's areas",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def list_areas(city_id: str) -> list[Area]:
    _require_city(city_id)
    return [Area(**a) for a in geography_service.list_areas(city_id)]


@router.get(
    "/api/cities/{city_id}/areas/{area_id}",
    response_model=Area,
    summary="Get one area",
    responses={404: {"model": ErrorResponse, "description": "City or area not found"}},
)
def get_area(city_id: str, area_id: int) -> Area:
    _require_city(city_id)
    area = geography_service.get_area(city_id, area_id)
    if area is None:
        raise DomainError(ErrorCode.AREA_NOT_FOUND, f"unknown area_id={area_id} for city_id={city_id!r}", 404)
    return Area(**area)


@router.get(
    "/api/cities/{city_id}/metrics",
    response_model=list[str],
    summary="List a city's available prediction metrics",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def list_metrics(city_id: str) -> list[str]:
    _require_city(city_id)
    return cities_registry.list_metrics(city_id)


@router.post(
    "/api/cities/{city_id}/predict/demand",
    response_model=PredictionEnvelope | CapabilityUnavailable,
    summary="City-scoped demand prediction",
    description="Delegates to the existing, unchanged model_service.py -- provenance-wrapped.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}, 400: {"model": ErrorResponse, "description": "Prediction failed"}},
)
def predict_demand(city_id: str, req: CityDemandPredictRequest) -> PredictionEnvelope | CapabilityUnavailable:
    return prediction_service.predict_demand(city_id, req.area_id, req.hour, req.day_of_week)


@router.post(
    "/api/cities/{city_id}/predict/fare",
    response_model=PredictionEnvelope | CapabilityUnavailable,
    summary="City-scoped fare prediction",
    description="Delegates to the existing, unchanged model_service.py -- provenance-wrapped.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}, 400: {"model": ErrorResponse, "description": "Prediction failed"}},
)
def predict_fare(city_id: str, req: CityFarePredictRequest) -> PredictionEnvelope | CapabilityUnavailable:
    return prediction_service.predict_fare(city_id, req.pickup_area_id, req.dropoff_area_id, req.hour)


@router.post(
    "/api/cities/{city_id}/journey/estimate",
    response_model=CityJourneyEstimate,
    summary="City-scoped journey estimate (any resolvable city)",
    description="Real OSRM route distance/duration for any city on Earth GeoNames can resolve, "
    "plus demand/fare -- computed for nyc/london where a real model exists, an honestly labeled "
    "modeled_estimate everywhere else. Not the full NYC-only /journey/estimate pipeline.",
    responses={404: {"model": ErrorResponse, "description": "City not resolvable"}},
)
def city_journey_estimate(city_id: str, req: CityJourneyRequest) -> CityJourneyEstimate:
    return city_journey_service.estimate(
        city_id, req.pickup_lat, req.pickup_lon, req.dropoff_lat, req.dropoff_lon, req.departure_time,
    )


@router.get(
    "/api/cities/{city_id}/forecast",
    response_model=ForecastEnvelope | CapabilityUnavailable,
    summary="City-scoped historical hourly profile (forecast proxy)",
    description="Real historical hourly aggregate from the mart, honestly labeled -- not a "
    "forward time-series forecast model.",
    responses={
        404: {"model": ErrorResponse, "description": "City not found"},
        400: {"model": ErrorResponse, "description": "Invalid time range"},
    },
)
def forecast(
    city_id: str,
    metric: str = Query("demand", description="demand or fare"),
    hours: int = Query(24, ge=1, le=24),
) -> ForecastEnvelope | CapabilityUnavailable:
    return prediction_service.forecast(city_id, metric, hours)


@router.post(
    "/api/cities/{city_id}/chat",
    response_model=ChatResponse,
    summary="City-scoped chat",
    description="Delegates to the existing, unchanged RAG pipeline -- city_id/area_id are context only this phase.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}, 500: {"model": ErrorResponse, "description": "Chat failed"}},
)
def city_chat(city_id: str, req: ChatRequest) -> ChatResponse:
    # Broadened existence check (any resolvable city, not registered-only)
    # -- chat never flatly refuses a real city, only a genuinely nonexistent
    # one 404s here.
    if global_geography_service.get_city_profile(city_id) is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    try:
        res = rag_service.answer_question(question=req.question, session_id=req.session_id, city_id=city_id)
    except Exception as exc:  # noqa: BLE001 -- surfaced as a typed DomainError, never a bare 500
        raise DomainError(ErrorCode.CHAT_FAILED, str(exc), 500) from exc
    return ChatResponse(
        answer=res["answer"], route=res["route"], sql=res.get("sql"), session_id=res["session_id"],
        city_id=city_id, area_id=req.area_id,
    )
