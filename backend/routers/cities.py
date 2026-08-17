"""City discovery + city-scoped predict/chat routes (SPEC-013 FR-9). Thin:
delegates to backend/registry/{countries,cities}.py, backend/services/
geography_service.py, backend/services/prediction_service.py, and the
existing (unchanged) backend/services/rag_service.py. Every pre-existing
route (`/predict/demand`, `/predict/fare`, `/zones`, `/chat`,
`/journey/estimate`) stays mounted, unchanged, in backend/main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger

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


def _global_city_to_city(c: dict) -> City:
    """Maps a global_cities row onto the same City shape search_cities()
    already builds -- so a country's listing includes its WorldMove-tier
    cities, not just the 2 fully-registered ones (see countries.py: the
    country's `supported` flag now reflects global_cities too, so this
    endpoint must actually return those cities or the two would disagree)."""
    return City(
        id=c.get("city_id", ""),
        name=c.get("name", ""),
        country_code=c.get("country_code", ""),
        latitude=c.get("latitude") if c.get("latitude") is not None else 0.0,
        longitude=c.get("longitude") if c.get("longitude") is not None else 0.0,
        timezone=c.get("timezone") or "UTC",
        currency=c.get("currency") or "USD",
        status=c.get("model_status", "unknown"),
        data_source=c.get("population_source", "unknown"),
        geography_type="zone",
        mobility_mode="ride_hailing",
        model_status=c.get("model_status", "unknown"),
        last_updated="",
    )


@router.get(
    "/api/countries/{code}/cities",
    response_model=list[City],
    summary="List a country's onboarded cities",
    tags=["Countries"],
    responses={404: {"model": ErrorResponse, "description": "Country not supported"}},
)
def list_country_cities(code: str) -> list[City]:
    from backend.registry import global_cities as global_cities_registry

    logger.info("GET /api/countries/{{code}}/cities step=start code={}", code)
    country = countries_registry.get_country(code)
    if country is None or not country["supported"]:
        logger.warning("GET /api/countries/{{code}}/cities step=country_not_supported code={}", code)
        raise DomainError(ErrorCode.COUNTRY_NOT_SUPPORTED, f"country not supported: {code!r}", 404)
    registered = [City(**c) for c in cities_registry.list_cities(country_code=code)]
    seen_ids = {c.id for c in registered}
    global_extra = [
        _global_city_to_city(c)
        for c in global_cities_registry.list_cities()
        if c.get("country_code", "").upper() == code.upper() and c.get("city_id") not in seen_ids
    ]
    cities = registered + global_extra
    logger.info("GET /api/countries/{{code}}/cities step=done code={} count={}", code, len(cities))
    return cities


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
    limit: int = Query(50, ge=1, le=2000),
) -> CitySearchResponse:
    from backend.registry import global_cities as global_cities_registry

    logger.info("GET /api/cities step=start q={!r} country={} tier={} supported={} page={} limit={}", q, country, tier, supported, page, limit)

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
            id=c.get("city_id", ""),
            name=c.get("name", ""),
            country_code=c.get("country_code", ""),
            latitude=c.get("latitude") if c.get("latitude") is not None else 0.0,
            longitude=c.get("longitude") if c.get("longitude") is not None else 0.0,
            timezone=c.get("timezone") or "UTC",
            currency=c.get("currency") or "USD",
            status=c.get("model_status", "unknown"),
            data_source=c.get("population_source", "unknown"),
            geography_type="zone",
            mobility_mode="ride_hailing",
            model_status=c.get("model_status", "unknown"),
            last_updated="",
        ))

    logger.info("GET /api/cities step=done total={} returned={}", total, len(results))
    return CitySearchResponse(results=results, total=total, page=page, limit=limit)


@router.get(
    "/api/cities/search",
    response_model=CitySearchResponse,
    summary="Search cities by name",
    description="Quick city name search.",
)
def search_cities_by_name(
    q: str | None = Query(None, description="City name to search for"),
    limit: int = Query(10, ge=1, le=2000),
) -> CitySearchResponse:
    from backend.registry import global_cities as global_cities_registry

    logger.info("GET /api/cities/search step=start q={!r} limit={}", q, limit)
    all_cities = global_cities_registry.list_cities()
    if q:
        q_lower = q.lower()
        all_cities = [c for c in all_cities if q_lower in c.get("name", "").lower() or q_lower in c.get("city_id", "").lower()]
    filtered = all_cities[:limit]

    results = []
    for c in filtered:
        results.append(City(
            id=c.get("city_id", ""),
            name=c.get("name", ""),
            country_code=c.get("country_code", ""),
            latitude=c.get("latitude") if c.get("latitude") is not None else 0.0,
            longitude=c.get("longitude") if c.get("longitude") is not None else 0.0,
            timezone=c.get("timezone") or "UTC",
            currency=c.get("currency") or "USD",
            status=c.get("model_status", "unknown"),
            data_source=c.get("population_source", "unknown"),
            geography_type="zone",
            mobility_mode="ride_hailing",
            model_status=c.get("model_status", "unknown"),
            last_updated="",
        ))

    logger.info("GET /api/cities/search step=done returned={}", len(results))
    return CitySearchResponse(results=results, total=len(results), page=1, limit=limit)


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
    # Not _require_city: capabilities resolve for any city in EITHER registry
    # (the 2-row `cities` seed or the 524-row `global_cities` table), so a
    # global city reports its real, mostly-false matrix instead of 404ing.
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
    # Broadened existence check (any resolvable city, not registered-only)
    # -- chat never flatly refuses a real city, only a genuinely nonexistent
    # one 404s here.
    if global_geography_service.get_city_profile(city_id) is None:
        logger.warning("POST /api/cities/{{city_id}}/chat step=city_not_resolvable city_id={}", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
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
    from backend.registry import global_cities as global_cities_registry
    from backend.services import tariff_profiles

    logger.info("GET /api/cities/{{city_id}}/profile step=start city_id={}", city_id)
    _validate_city_id(city_id)

    profile = global_cities_registry.get_city(city_id)
    if not profile:
        # Try cities registry
        profile = cities_registry.get_city(city_id)
    if not profile:
        logger.warning("GET /api/cities/{{city_id}}/profile step=not_found city_id={}", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)

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
        data_source=profile.get("population_source") or "unknown",
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


@router.websocket("/api/cities/{city_id}/tariff/enrich")
async def websocket_tariff_enrich(websocket: WebSocket, city_id: str):
    """On-demand tariff enrichment, streamed. A city page opens this when
    its cached tariff has no `validation_method` yet (never evidence/
    analytically validated) -- the client sees "agent is analyzing..."
    status messages in real time instead of a silent wait, then the final
    profile. See backend/services/tariff_enrichment.py's module docstring
    for why this is the one deliberate exception to "no LLM call on a
    request path" in this repo, and why it's safe (serialized per city_id,
    fires once ever per city, never on the hot fare-lookup path)."""
    from backend.services import tariff_enrichment, tariff_profiles

    await websocket.accept()
    logger.info("WS /api/cities/{{city_id}}/tariff/enrich step=accepted city_id={}", city_id)
    if cities_registry.get_city(city_id) is not None:
        # nyc/london are the two registered reference cities -- they price
        # from a real trained fare model (pricing_engine._base_fare), never
        # a tariff profile (see tariff_profiles.py's module docstring and
        # find_cities_needing_tariff_validation.py's same exclusion for the
        # offline path). Without this guard, opening either city's page
        # fires this WS (TariffCard.tsx's needsEnrichment sees no cached
        # profile) and writes a bogus, never-used tariff row for it -- found
        # 2026-08-16 after exactly that happened in Postgres.
        logger.info("WS /api/cities/{{city_id}}/tariff/enrich step=skipped_reference_city city_id={}", city_id)
        await websocket.send_json({
            "type": "error",
            "message": "this city prices from a trained fare model, not a tariff profile",
        })
        await websocket.close()
        return
    try:
        cached = tariff_profiles.get(city_id)
        if cached is not None and cached.validation_method is not None:
            from dataclasses import asdict as _asdict

            await websocket.send_json({"type": "result", "profile": _asdict(cached), "cached": True})
            await websocket.close()
            return

        await tariff_enrichment.stream_enrichment_over_websocket(websocket, city_id)
        await websocket.close()
        logger.info("WS /api/cities/{{city_id}}/tariff/enrich step=done city_id={}", city_id)
    except WebSocketDisconnect:
        logger.info("WS /api/cities/{{city_id}}/tariff/enrich step=client_disconnected city_id={}", city_id)
    except Exception:
        # Never forward str(exc) to the client -- see chat.py's WS for the
        # same discipline and the incident that motivated it.
        logger.exception("WS /api/cities/{{city_id}}/tariff/enrich failed city_id={}", city_id)
        try:
            await websocket.send_json({"type": "error", "message": "something went wrong enriching this city's tariff data"})
            await websocket.close(code=1011)
        except Exception:
            pass


@router.get(
    "/api/cities/{city_id}/zones",
    response_model=CityZonesResponse,
    summary="Get city zones",
    description="Zone metadata for cities that support zone-based predictions.",
)
def get_city_zones(city_id: str) -> CityZonesResponse:
    logger.info("GET /api/cities/{{city_id}}/zones step=start city_id={}", city_id)
    # Check if city has zones (NYC only currently)
    city = cities_registry.get_city(city_id)
    if city is None:
        # Check global cities
        from backend.registry import global_cities as global_cities_registry
        city = global_cities_registry.get_city(city_id)

    if city is None:
        logger.warning("GET /api/cities/{{city_id}}/zones step=not_found city_id={}", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)

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
