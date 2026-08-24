"""City capability routes (ADR-013).

One city is served (ADR-012), so these no longer carry a `/api/cities/{city_id}`
prefix -- each is mounted at its bare `/api/...` path.

Seven routes that used to live here are gone rather than renamed:

* `predict/demand`, `predict/fare`, `journey/estimate`, `chat` and `zones`
  were duplicates of the un-prefixed routes in predictions.py, journey.py,
  chat.py and zones.py, which every caller (the frontend included) can use
  directly.
* `GET /api/cities` searched a registry of one row, and `GET /api/cities/{id}`
  returned a strict subset of `/api/profile`.

Thin: delegates to backend/registry/cities.py, backend/services/
geography_service.py, and backend/services/prediction_service.py.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from loguru import logger

from backend.errors import DomainError
from backend.registry import CITY_ID
from backend.registry import cities as cities_registry
from backend.schemas import (
    Area,
    CapabilityUnavailable,
    Capabilities,
    CityContextResponse,
    CityProfileResponse,
    CityTariffResponse,
    ErrorCode,
    ErrorResponse,
    ForecastEnvelope,
)
from backend.services import (
    context_orchestrator,
    geography_service,
    prediction_service,
    tariff_profiles,
)

router = APIRouter(tags=["City"])

_NO_CITY = {404: {"model": ErrorResponse, "description": "No registered city row"}}


def _require_city() -> dict:
    city = cities_registry.get_city()
    if city is None:
        logger.warning("step=require_city failed reason=no_registered_city")
        raise DomainError(ErrorCode.CITY_NOT_FOUND, "no registered city row", 404)
    return city


@router.get(
    "/api/capabilities",
    response_model=Capabilities,
    summary="The platform's real, wired capabilities",
    description="Never aspirational -- demand/fare/journey are true iff an active "
    "model_registry row backs them, area_analysis iff canonical_areas has rows.",
    responses=_NO_CITY,
)
def get_capabilities() -> Capabilities:
    logger.info("GET /api/capabilities step=start")
    capabilities = cities_registry.get_capabilities()
    if capabilities is None:
        logger.warning("GET /api/capabilities step=not_found")
        raise DomainError(ErrorCode.CITY_NOT_FOUND, "no registered city row", 404)
    logger.info("GET /api/capabilities step=done")
    return Capabilities(**capabilities)


@router.get(
    "/api/areas",
    response_model=list[Area],
    summary="List the city's areas",
    responses=_NO_CITY,
)
def list_areas() -> list[Area]:
    logger.info("GET /api/areas step=start")
    _require_city()
    areas = [Area(**a) for a in geography_service.list_areas()]
    logger.info("GET /api/areas step=done count={}", len(areas))
    return areas


@router.get(
    "/api/areas/{area_id}",
    response_model=Area,
    summary="Get one area",
    responses={404: {"model": ErrorResponse, "description": "Area not found"}},
)
def get_area(area_id: int) -> Area:
    logger.info("GET /api/areas/{{area_id}} step=start area_id={}", area_id)
    _require_city()
    area = geography_service.get_area(area_id)
    if area is None:
        logger.warning("GET /api/areas/{{area_id}} step=not_found area_id={}", area_id)
        raise DomainError(ErrorCode.AREA_NOT_FOUND, f"unknown area_id={area_id}", 404)
    logger.info("GET /api/areas/{{area_id}} step=done area_id={}", area_id)
    return Area(**area)


@router.get(
    "/api/metrics",
    response_model=list[str],
    summary="List the available prediction metrics",
    responses=_NO_CITY,
)
def list_metrics() -> list[str]:
    logger.info("GET /api/metrics step=start")
    _require_city()
    metrics = cities_registry.list_metrics()
    logger.info("GET /api/metrics step=done metrics={}", metrics)
    return metrics


@router.get(
    "/api/forecast",
    response_model=ForecastEnvelope | CapabilityUnavailable,
    summary="Historical hourly profile (forecast proxy)",
    description="Real historical hourly aggregate from the mart, honestly labeled -- not a "
    "forward time-series forecast model.",
    responses={
        404: {"model": ErrorResponse, "description": "No registered city row"},
        400: {"model": ErrorResponse, "description": "Invalid time range"},
    },
)
def forecast(
    metric: str = Query("demand", description="demand or fare"),
    hours: int = Query(24, ge=1, le=24),
) -> ForecastEnvelope | CapabilityUnavailable:
    logger.info("GET /api/forecast step=start metric={} hours={}", metric, hours)
    result = prediction_service.forecast(metric, hours)
    logger.info("GET /api/forecast step=done")
    return result


@router.get(
    "/api/profile",
    response_model=CityProfileResponse,
    summary="Complete city profile",
    description="Identity, capabilities, and data availability for the served city.",
    responses=_NO_CITY,
)
def get_city_profile() -> CityProfileResponse:
    logger.info("GET /api/profile step=start")
    profile = _require_city()

    capabilities = cities_registry.capability_matrix() or {}
    tariff = tariff_profiles.get()

    logger.info("GET /api/profile step=done")
    return CityProfileResponse(
        id=CITY_ID,
        name=profile.get("name") or CITY_ID,
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
    "/api/tariff",
    response_model=CityTariffResponse,
    summary="Tariff profile",
    description="The real cached TariffProfile backing the fare estimate.",
)
def get_city_tariff() -> CityTariffResponse:
    logger.info("GET /api/tariff step=start")
    profile = tariff_profiles.get()
    if profile is None:
        logger.info("GET /api/tariff step=no_tariff_profile")
        return CityTariffResponse(available=False, city_id=CITY_ID, reason="no_tariff_profile")

    data = asdict(profile)
    data["available"] = True
    data["city_id"] = CITY_ID
    logger.info("GET /api/tariff step=done")
    return CityTariffResponse(**data)


@router.get(
    "/api/context",
    response_model=CityContextResponse,
    summary="Real environmental/urban context",
    description="Geography, weather, calendar, urban density, routing capability and "
    "demand shape, each in a standardized provenance envelope. An unavailable source "
    "carries a real reason, never a fabricated value.",
    responses=_NO_CITY,
)
def get_city_context() -> CityContextResponse:
    logger.info("GET /api/context step=start")
    _require_city()
    context_data = context_orchestrator.get_city_context()
    logger.info("GET /api/context step=done")
    return CityContextResponse(**context_data)
