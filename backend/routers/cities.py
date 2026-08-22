"""City discovery + city-scoped predict/chat routes. Thin:
delegates to backend/registry/cities.py, backend/services/
geography_service.py, backend/services/prediction_service.py, and the
existing (unchanged) backend/services/rag_service.py. Every pre-existing
route (`/predict/demand`, `/predict/fare`, `/zones`, `/chat`,
`/journey/estimate`) stays mounted, unchanged, in backend/main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from loguru import logger

from backend.errors import DomainError
from backend.registry import cities as cities_registry
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
    CityContextResponse,
    CityJourneyRequest,
    CityProfileResponse,
    CitySearchResponse,
    CityTariffResponse,
    CityZonesResponse,
    ErrorCode,
    ErrorResponse,
    ForecastEnvelope,
    PredictionEnvelope,
    Zone,
)
from backend.services import (
    city_journey_service,
    geography_service,
    prediction_service,
    rag_service,
    tariff_profiles,
)

router = APIRouter(tags=["Cities"])


# IDs that are JavaScript artefacts or clearly invalid — reject immediately
# so they never pollute registry logs or hit the DB.
_INVALID_CITY_IDS = frozenset({"undefined", "null", "none", "", "0", "false"})


def _validate_city_id(city_id: str) -> None:
    """Raise 400 if city_id is obviously malformed (JS artefact, empty, too long)."""
    if city_id.lower() in _INVALID_CITY_IDS or len(city_id) > 80:
        raise DomainError(
            ErrorCode.CITY_NOT_FOUND,
            f"invalid city_id={city_id!r}: must be a valid city identifier",
            400,
        )


def _require_city(city_id: str) -> dict:
    _validate_city_id(city_id)
    city = cities_registry.get_city(city_id)
    if city is None:
        logger.warning("step=require_city failed city_id={} reason=not_found", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return city


@router.get(
    "/api/cities",
    response_model=CitySearchResponse,
    summary="List registered cities",
    description="Every city this platform has real trip data for (ADR-011).",
)
def search_cities(
    q: str | None = Query(None, description="Filter by name or id substring"),
    country: str | None = Query(None, description="Country code filter"),
) -> CitySearchResponse:
    logger.info("GET /api/cities step=start q={!r} country={}", q, country)
    rows = cities_registry.list_cities(country_code=country)
    if q:
        q_lower = q.lower()
        rows = [c for c in rows if q_lower in c["name"].lower() or q_lower in c["id"].lower()]
    results = [City(**c) for c in rows]
    logger.info("GET /api/cities step=done returned={}", len(results))
    return CitySearchResponse(results=results, total=len(results), page=1, limit=len(results))


@router.get(
    "/api/cities/{city_id}",
    response_model=City,
    summary="Get a city",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def get_city(city_id: str) -> City:
    logger.info("GET /api/cities/{{city_id}} step=start city_id={}", city_id)
    city = City(**_require_city(city_id))
    logger.info("GET /api/cities/{{city_id}} step=done city_id={}", city_id)
    return city


@router.get(
    "/api/cities/{city_id}/capabilities",
    response_model=Capabilities,
    summary="Get a city's real, wired capabilities",
    description="Never aspirational -- demand/fare/journey are true iff an active "
    "model_registry row backs them, area_analysis iff canonical_areas has rows for this city.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def get_capabilities(city_id: str) -> Capabilities:
    logger.info("GET /api/cities/{{city_id}}/capabilities step=start city_id={}", city_id)
    _validate_city_id(city_id)
    capabilities = cities_registry.get_capabilities(city_id)
    if capabilities is None:
        logger.warning("GET /api/cities/{{city_id}}/capabilities step=not_found city_id={}", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    logger.info("GET /api/cities/{{city_id}}/capabilities step=done city_id={}", city_id)
    return Capabilities(**capabilities)


@router.get(
    "/api/cities/{city_id}/areas",
    response_model=list[Area],
    summary="List a city's areas",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def list_areas(city_id: str) -> list[Area]:
    logger.info("GET /api/cities/{{city_id}}/areas step=start city_id={}", city_id)
    _require_city(city_id)
    areas = [Area(**a) for a in geography_service.list_areas(city_id)]
    logger.info("GET /api/cities/{{city_id}}/areas step=done city_id={} count={}", city_id, len(areas))
    return areas


@router.get(
    "/api/cities/{city_id}/areas/{area_id}",
    response_model=Area,
    summary="Get one area",
    responses={404: {"model": ErrorResponse, "description": "City or area not found"}},
)
def get_area(city_id: str, area_id: int) -> Area:
    logger.info("GET /api/cities/{{city_id}}/areas/{{area_id}} step=start city_id={} area_id={}", city_id, area_id)
    _require_city(city_id)
    area = geography_service.get_area(city_id, area_id)
    if area is None:
        logger.warning("GET /api/cities/{{city_id}}/areas/{{area_id}} step=not_found city_id={} area_id={}", city_id, area_id)
        raise DomainError(ErrorCode.AREA_NOT_FOUND, f"unknown area_id={area_id} for city_id={city_id!r}", 404)
    logger.info("GET /api/cities/{{city_id}}/areas/{{area_id}} step=done city_id={} area_id={}", city_id, area_id)
    return Area(**area)


@router.get(
    "/api/cities/{city_id}/metrics",
    response_model=list[str],
    summary="List a city's available prediction metrics",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def list_metrics(city_id: str) -> list[str]:
    logger.info("GET /api/cities/{{city_id}}/metrics step=start city_id={}", city_id)
    _require_city(city_id)
    metrics = cities_registry.list_metrics(city_id)
    logger.info("GET /api/cities/{{city_id}}/metrics step=done city_id={} metrics={}", city_id, metrics)
    return metrics


@router.post(
    "/api/cities/{city_id}/predict/demand",
    response_model=PredictionEnvelope | CapabilityUnavailable,
    summary="City-scoped demand prediction",
    description="Delegates to the existing, unchanged model_service.py -- provenance-wrapped.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}, 400: {"model": ErrorResponse, "description": "Prediction failed"}},
)
def predict_demand(city_id: str, req: CityDemandPredictRequest) -> PredictionEnvelope | CapabilityUnavailable:
    logger.info("POST /api/cities/{{city_id}}/predict/demand step=start city_id={} area_id={} hour={}", city_id, req.area_id, req.hour)
    result = prediction_service.predict_demand(city_id, req.area_id, req.hour, req.day_of_week)
    logger.info("POST /api/cities/{{city_id}}/predict/demand step=done city_id={}", city_id)
    return result


@router.post(
    "/api/cities/{city_id}/predict/fare",
    response_model=PredictionEnvelope | CapabilityUnavailable,
    summary="City-scoped fare prediction",
    description="Delegates to the existing, unchanged model_service.py -- provenance-wrapped.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}, 400: {"model": ErrorResponse, "description": "Prediction failed"}},
)
def predict_fare(city_id: str, req: CityFarePredictRequest) -> PredictionEnvelope | CapabilityUnavailable:
    logger.info("POST /api/cities/{{city_id}}/predict/fare step=start city_id={} pickup_area_id={} dropoff_area_id={} hour={}", city_id, req.pickup_area_id, req.dropoff_area_id, req.hour)
    result = prediction_service.predict_fare(city_id, req.pickup_area_id, req.dropoff_area_id, req.hour)
    logger.info("POST /api/cities/{{city_id}}/predict/fare step=done city_id={}", city_id)
    return result


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
    logger.info("POST /api/cities/{{city_id}}/journey/estimate step=start city_id={}", city_id)
    result = city_journey_service.estimate(
        city_id, req.pickup_lat, req.pickup_lon, req.dropoff_lat, req.dropoff_lon, req.departure_time,
    )
    logger.info("POST /api/cities/{{city_id}}/journey/estimate step=done city_id={}", city_id)
    return result


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
    logger.info("GET /api/cities/{{city_id}}/forecast step=start city_id={} metric={} hours={}", city_id, metric, hours)
    result = prediction_service.forecast(city_id, metric, hours)
    logger.info("GET /api/cities/{{city_id}}/forecast step=done city_id={}", city_id)
    return result


@router.post(
    "/api/cities/{city_id}/chat",
    response_model=ChatResponse,
    summary="City-scoped chat",
    description="Delegates to the existing, unchanged RAG pipeline -- city_id/area_id are context only this phase.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}, 500: {"model": ErrorResponse, "description": "Chat failed"}},
)
def city_chat(city_id: str, req: ChatRequest) -> ChatResponse:
    logger.info("POST /api/cities/{{city_id}}/chat step=start city_id={} session_id={}", city_id, req.session_id)
    _require_city(city_id)
    try:
        res = rag_service.answer_question(question=req.question, session_id=req.session_id, city_id=city_id)
    except Exception as exc:  # noqa: BLE001 -- surfaced as a typed DomainError, never a bare 500
        logger.exception("POST /api/cities/{{city_id}}/chat step=rag_service.answer_question failed city_id={}", city_id)
        raise DomainError(ErrorCode.CHAT_FAILED, str(exc), 500) from exc
    logger.info("POST /api/cities/{{city_id}}/chat step=done city_id={}", city_id)
    return ChatResponse(
        answer=res["answer"], route=res["route"], sql=res.get("sql"), session_id=res["session_id"],
        city_id=city_id, area_id=req.area_id,
    )


# ── New Granular City APIs (Part 2 API Decomposition) ───────────────────────────



@router.get(
    "/api/cities/{city_id}/profile",
    response_model=CityProfileResponse,
    summary="Get complete city profile",
    description="Full city profile with identity, capabilities, and data availability.",
)
def get_city_profile(city_id: str) -> CityProfileResponse:
    logger.info("GET /api/cities/{{city_id}}/profile step=start city_id={}", city_id)
    profile = _require_city(city_id)

    capabilities = cities_registry.capability_matrix(city_id) or {}
    tariff = tariff_profiles.get(city_id)

    logger.info("GET /api/cities/{{city_id}}/profile step=done city_id={}", city_id)
    return CityProfileResponse(
        id=city_id,
        name=profile.get("name") or city_id,
        country_code=profile.get("country_code") or "XX",
        country=profile.get("country_code") or "XX",
        latitude=profile.get("latitude") or 0.0,
        longitude=profile.get("longitude") or 0.0,
        timezone=profile.get("timezone") or "UTC",
        currency=profile.get("currency") or "USD",
        tier=profile.get("model_status") or "unknown",
        population=int(round(profile["population"])) if profile.get("population") is not None else None,
        model_status=profile.get("model_status") or "unknown",
        data_source=profile.get("data_source") or "unknown",
        geography_type=profile.get("geography_type") or "zone",
        mobility_mode=profile.get("mobility_mode") or "ride_hailing",
        confidence=tariff.confidence if tariff else 0.0,
        data_availability={
            "demand": capabilities.get("demand", False),
            "fare": capabilities.get("fare", False),
            "routing": capabilities.get("routing", False),
            "congestion": capabilities.get("congestion", False),
            "availability": capabilities.get("availability", False),
            "surge": capabilities.get("surge", False),
            "carbon": capabilities.get("carbon", False),
            "best_departure": capabilities.get("best_departure", False),
        },
    )


@router.get(
    "/api/cities/{city_id}/tariff",
    response_model=CityTariffResponse,
    summary="Get city tariff profile",
    description="The real cached TariffProfile backing this city's fare estimate.",
)
def get_city_tariff(city_id: str) -> CityTariffResponse:
    from backend.services import tariff_profiles
    from dataclasses import asdict

    logger.info("GET /api/cities/{{city_id}}/tariff step=start city_id={}", city_id)
    profile = tariff_profiles.get(city_id)
    if profile is None:
        logger.info("GET /api/cities/{{city_id}}/tariff step=no_tariff_profile city_id={}", city_id)
        return CityTariffResponse(available=False, city_id=city_id, reason="no_tariff_profile")

    data = asdict(profile)
    data["available"] = True
    data["city_id"] = city_id
    logger.info("GET /api/cities/{{city_id}}/tariff step=done city_id={}", city_id)
    return CityTariffResponse(**data)


@router.get(
    "/api/cities/{city_id}/context",
    response_model=CityContextResponse,
    summary="Real environmental/urban context for a city",
    description="Geography, weather, calendar, urban density, routing capability and "
    "demand shape, each in a standardized provenance envelope. An unavailable source "
    "carries a real reason, never a fabricated value.",
    responses={404: {"model": ErrorResponse, "description": "City not found"}},
)
def get_city_context(city_id: str) -> CityContextResponse:
    from backend.services import context_orchestrator

    logger.info("GET /api/cities/{{city_id}}/context step=start city_id={}", city_id)
    _require_city(city_id)
    context_data = context_orchestrator.get_city_context(city_id)
    logger.info("GET /api/cities/{{city_id}}/context step=done city_id={}", city_id)
    return CityContextResponse(**context_data)


@router.get(
    "/api/cities/{city_id}/zones",
    response_model=CityZonesResponse,
    summary="Get city zones",
    description="Zone metadata for cities that support zone-based predictions.",
)
def get_city_zones(city_id: str) -> CityZonesResponse:
    logger.info("GET /api/cities/{{city_id}}/zones step=start city_id={}", city_id)
    _require_city(city_id)

    # Only NYC has zones in our system
    if city_id != "nyc":
        logger.info("GET /api/cities/{{city_id}}/zones step=zones_not_supported city_id={}", city_id)
        return CityZonesResponse(
            available=False,
            city_id=city_id,
            reason="zones_not_supported",
            zones=None,
        )

    # NYC zones
    from backend.routers import zones as zones_router
    zone_list = zones_router.list_zones()

    logger.info("GET /api/cities/{{city_id}}/zones step=done city_id={} count={}", city_id, len(zone_list))
    return CityZonesResponse(
        available=True,
        city_id=city_id,
        reason=None,
        zones=zone_list,
    )
