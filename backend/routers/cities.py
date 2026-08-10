"""City discovery + city-scoped predict/chat routes (SPEC-013 FR-9). Thin:
delegates to backend/registry/{countries,cities}.py, backend/services/
geography_service.py, backend/services/prediction_service.py, and the
existing (unchanged) backend/services/rag_service.py. Every pre-existing
route (`/predict/demand`, `/predict/fare`, `/zones`, `/chat`,
`/journey/estimate`) stays mounted, unchanged, in backend/main.py.
"""
from __future__ import annotations

from dataclasses import asdict

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
    CityProfileResponse,
    CityCapabilitiesResponse,
    CitySearchRequest,
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
    global_geography_service,
    prediction_service,
    rag_service,
    tariff_profiles,
)

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
    # Not _require_city: capabilities resolve for any city in EITHER registry
    # (the 2-row `cities` seed or the 524-row `global_cities` table), so a
    # global city reports its real, mostly-false matrix instead of 404ing.
    capabilities = cities_registry.get_capabilities(city_id)
    if capabilities is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return Capabilities(**capabilities)


@router.get(
    "/api/cities/{city_id}/tariff",
    summary="Get a city's fare tariff profile",
    description="The real cached TariffProfile backing this city's fare estimate, or "
    "{'available': false, 'reason': 'no_tariff_profile'} -- never a fabricated rate. "
    "Read-only: profiles are written offline by scripts/generate_tariff_profile.py, "
    "never from a request path (rule 8).",
)
def get_tariff(city_id: str) -> dict:
    profile = tariff_profiles.get(city_id)
    if profile is None:
        return {"available": False, "reason": "no_tariff_profile", "city_id": city_id}
    return {"available": True, **asdict(profile)}


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


# ── New Granular City APIs (Part 2 API Decomposition) ───────────────────────────


@router.get(
    "/api/cities",
    response_model=CitySearchResponse,
    summary="List/Search cities with filters",
    description="Search and filter cities by query, country, tier, and supported status.",
)
def search_cities(
    q: str | None = Query(None, description="Search query (name)"),
    country: str | None = Query(None, description="Country code filter"),
    tier: str | None = Query(None, description="Tier filter: OBSERVED or TRANSFER"),
    supported: bool | None = Query(None, description="Filter by supported status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> CitySearchResponse:
    from backend.registry import global_cities as global_cities_registry

    all_cities = global_cities_registry.list_cities()

    # Apply filters
    if q:
        q_lower = q.lower()
        all_cities = [c for c in all_cities if q_lower in c.get("name", "").lower() or q_lower in c.get("city_id", "").lower()]

    if country:
        all_cities = [c for c in all_cities if c.get("country_code", "").upper() == country.upper()]

    if tier:
        all_cities = [c for c in all_cities if c.get("model_status", "").upper() == tier.upper()]

    if supported is not None:
        all_cities = [c for c in all_cities if (cities_registry.get_city(c["city_id"]) is not None) == supported]

    total = len(all_cities)
    start = (page - 1) * limit
    end = start + limit
    paginated = all_cities[start:end]

    # Convert to City model
    results = []
    for c in paginated:
        results.append(City(
            id=c["city_id"],
            name=c["name"],
            country_code=c["country_code"],
            latitude=c["latitude"],
            longitude=c["longitude"],
            timezone=c.get("timezone", "UTC"),
            currency=c.get("currency", "USD"),
            status=c.get("model_status", "unknown"),
            data_source=c.get("population_source", "unknown"),
            geography_type="zone",
            mobility_mode="ride_hailing",
            model_status=c.get("model_status", "unknown"),
            last_updated="",
        ))

    return CitySearchResponse(results=results, total=total, page=page, limit=limit)


@router.get(
    "/api/cities/search",
    response_model=CitySearchResponse,
    summary="Search cities by name",
    description="Quick city name search.",
)
def search_cities_by_name(
    q: str = Query(..., min_length=1, description="City name to search for"),
    limit: int = Query(10, ge=1, le=50),
) -> CitySearchResponse:
    from backend.registry import global_cities as global_cities_registry

    all_cities = global_cities_registry.list_cities()
    q_lower = q.lower()
    filtered = [c for c in all_cities if q_lower in c.get("name", "").lower() or q_lower in c.get("city_id", "").lower()]
    filtered = filtered[:limit]

    results = []
    for c in filtered:
        results.append(City(
            id=c["city_id"],
            name=c["name"],
            country_code=c["country_code"],
            latitude=c["latitude"],
            longitude=c["longitude"],
            timezone=c.get("timezone", "UTC"),
            currency=c.get("currency", "USD"),
            status=c.get("model_status", "unknown"),
            data_source=c.get("population_source", "unknown"),
            geography_type="zone",
            mobility_mode="ride_hailing",
            model_status=c.get("model_status", "unknown"),
            last_updated="",
        ))

    return CitySearchResponse(results=results, total=len(results), page=1, limit=limit)


@router.get(
    "/api/cities/{city_id}/profile",
    response_model=CityProfileResponse,
    summary="Get complete city profile",
    description="Full city profile with identity, capabilities, and data availability.",
)
def get_city_profile(city_id: str) -> CityProfileResponse:
    from backend.registry import global_cities as global_cities_registry
    from backend.services import tariff_profiles

    profile = global_cities_registry.get_city(city_id)
    if not profile:
        # Try cities registry
        profile = cities_registry.get_city(city_id)
    if not profile:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)

    capabilities = cities_registry.capability_matrix(city_id) or {}
    tariff = tariff_profiles.get(city_id)

    return CityProfileResponse(
        id=city_id,
        name=profile.get("name", city_id),
        country_code=profile.get("country_code", "XX"),
        country=profile.get("country_code", "XX"),
        latitude=profile.get("latitude", 0.0),
        longitude=profile.get("longitude", 0.0),
        timezone=profile.get("timezone", "UTC"),
        currency=profile.get("currency", "USD"),
        tier=profile.get("model_status", "unknown"),
        population=profile.get("population"),
        model_status=profile.get("model_status", "unknown"),
        data_source=profile.get("population_source", "unknown"),
        geography_type=profile.get("geography_type", "zone"),
        mobility_mode=profile.get("mobility_mode", "ride_hailing"),
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
    "/api/cities/{city_id}/capabilities",
    response_model=CityCapabilitiesResponse,
    summary="Get city capabilities",
    description="Real, wired capabilities derived from actual backend support.",
)
def get_city_capabilities(city_id: str) -> CityCapabilitiesResponse:
    capabilities = cities_registry.capability_matrix(city_id)
    if capabilities is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return CityCapabilitiesResponse(city_id=city_id, capabilities=capabilities)


@router.get(
    "/api/cities/{city_id}/tariff",
    response_model=CityTariffResponse,
    summary="Get city tariff profile",
    description="The real cached TariffProfile backing this city's fare estimate.",
)
def get_city_tariff(city_id: str) -> CityTariffResponse:
    from backend.services import tariff_profiles
    from dataclasses import asdict

    profile = tariff_profiles.get(city_id)
    if profile is None:
        return CityTariffResponse(available=False, city_id=city_id, reason="no_tariff_profile")

    data = asdict(profile)
    data["available"] = True
    data["city_id"] = city_id
    return CityTariffResponse(**data)


@router.get(
    "/api/cities/{city_id}/zones",
    response_model=CityZonesResponse,
    summary="Get city zones",
    description="Zone metadata for cities that support zone-based predictions.",
)
def get_city_zones(city_id: str) -> CityZonesResponse:
    # Check if city has zones (NYC only currently)
    city = cities_registry.get_city(city_id)
    if city is None:
        # Check global cities
        from backend.registry import global_cities as global_cities_registry
        city = global_cities_registry.get_city(city_id)

    if city is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)

    # Only NYC has zones in our system
    if city_id != "nyc":
        return CityZonesResponse(
            available=False,
            city_id=city_id,
            reason="zones_not_supported",
            zones=None,
        )

    # NYC zones
    from backend.routers import zones as zones_router
    zone_list = zones_router.list_zones()

    return CityZonesResponse(
        available=True,
        city_id=city_id,
        reason=None,
        zones=zone_list,
    )
