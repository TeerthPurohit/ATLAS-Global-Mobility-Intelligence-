"""Prediction orchestrator (SPEC-013 FR-7): resolve city -> check capability
against the city's registered row -> resolve model via `model_registry` ->
call the existing, UNCHANGED `model_service.py` functions -> wrap the result
in a provenance envelope. This is a thin orchestration layer, not a second
prediction implementation -- every number it returns is exactly what
`model_service.py` already computed (rule 8: no new inference/training path).

A capability that genuinely isn't wired for a city returns a
`CapabilityUnavailable` 200 body (never a fabricated number, matching the
`/journey/estimate` "data unavailable != 4xx for a well-formed request"
precedent). A missing city/area, or a real failure resolving a known-valid
request (e.g. an unrecognized area_id), raises `DomainError` -- the router
translates that to a 404/400 `ErrorResponse`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from backend.datasources import get_datasource
from backend.errors import DomainError
from backend.registry import models as models_registry
from backend.schemas import (
    CapabilityUnavailable,
    ErrorCode,
    ForecastEnvelope,
    ForecastPoint,
    PredictionEnvelope,
)
from backend.services import estimation_service, geography_service, global_geography_service, model_service, pricing_engine, tariff_profiles

_FORECASTABLE_METRICS = ("demand", "fare")


def _require_city(city_id: str) -> dict:
    """Broadened per the "any resolvable city, never a bare 404" design
    decision: resolves via global_geography_service (real GeoNames geocoding
    for any city on Earth), not the registered-cities-only cities_registry.
    Only genuinely unresolvable input (e.g. a nonexistent place name) 404s."""
    profile = global_geography_service.get_city_profile(city_id)
    if profile is None:
        logger.info("prediction_service._require_city step=not_resolvable city_id={}", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return profile


def _envelope(
    city_id: str, area_id: int | None, dropoff_area_id: int | None, metric: str,
    value: float, model_name: str, basis: str = "computed", reason: str | None = None,
) -> PredictionEnvelope:
    model_meta = models_registry.get_model(model_name)
    logger.info("prediction_service._envelope step=model_resolved model={} city_id={} metric={} basis={}", model_name, city_id, metric, basis)
    return PredictionEnvelope(
        city_id=city_id,
        area_id=area_id,
        dropoff_area_id=dropoff_area_id,
        metric=metric,
        prediction=value,
        model=model_name,
        model_version=(model_meta or {}).get("version"),
        generated_at=datetime.now(timezone.utc),
        data_timestamp=None,
        source=(model_meta or {}).get("metrics_ref") or "model_service",
        basis=basis,
        reason=reason,
    )


def predict_demand(city_id: str, area_id: int, hour: int, day_of_week: int) -> PredictionEnvelope | CapabilityUnavailable:
    logger.info("prediction_service.predict_demand step=start city_id={} area_id={} hour={}", city_id, area_id, hour)
    profile = _require_city(city_id)
    if models_registry.resolve_model(city_id, "demand") is not None:
        try:
            value, model_name = model_service.predict_demand(area_id, hour, day_of_week, city_id=city_id)
        except KeyError as exc:
            logger.info("prediction_service.predict_demand step=model_service.predict_demand failed city_id={} reason={}", city_id, exc)
            raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
        return _envelope(city_id, area_id, None, "demand", value, model_name, basis="computed")

    # No trained model for this city -- fall through to the real, honestly
    # labeled cross-city estimate instead of stopping at CapabilityUnavailable,
    # per the "any resolvable city gets a real answer" design decision.
    population = profile.get("population")
    if population is None:
        logger.info("prediction_service.predict_demand step=capability_unavailable city_id={} reason=no_model_no_population", city_id)
        return CapabilityUnavailable(
            available=False, capability="demand",
            reason=f"no active demand model and no population covariate for city_id={city_id!r}",
        )
    result = estimation_service.estimate_city_demand(city_id, population)
    if result.basis != "modeled_estimate" or result.value is None:
        return CapabilityUnavailable(available=False, capability="demand", reason=result.reason)
    return _envelope(city_id, area_id, None, "demand", result.value, "cross_city_estimation", basis="modeled_estimate")


def predict_fare(city_id: str, pickup_area_id: int, dropoff_area_id: int, hour: int) -> PredictionEnvelope | CapabilityUnavailable:
    logger.info("prediction_service.predict_fare step=start city_id={} pickup_area_id={} dropoff_area_id={}", city_id, pickup_area_id, dropoff_area_id)
    _require_city(city_id)
    if models_registry.resolve_model(city_id, "fare") is not None:
        try:
            value, model_name = model_service.predict_fare(pickup_area_id, dropoff_area_id, hour)
        except KeyError as exc:
            logger.info("prediction_service.predict_fare step=model_service.predict_fare failed city_id={} reason={}", city_id, exc)
            raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
        return _envelope(city_id, pickup_area_id, dropoff_area_id, "fare", value, model_name, basis="computed")

    # No trained fare model -- fall through to the tariff-profile estimate,
    # same source cities.py's capability matrix already promises via
    # `fare = has_fare_model or has_tariff` (this endpoint used to only ever
    # check has_fare_model, so capabilities.fare=True for a TRANSFER city
    # while this call 200'd CapabilityUnavailable -- a contradiction the
    # /api/mobility/fare path never had, since it went through pricing_engine
    # directly).
    if tariff_profiles.get(city_id) is None:
        logger.info("prediction_service.predict_fare step=capability_unavailable city_id={} reason=no_model_no_tariff", city_id)
        return CapabilityUnavailable(
            available=False, capability="fare",
            reason=f"no active fare model and no tariff profile for city_id={city_id!r}",
        )
    pickup = geography_service.get_area(city_id, pickup_area_id)
    dropoff = geography_service.get_area(city_id, dropoff_area_id)
    if not pickup or not dropoff or pickup["latitude"] is None or dropoff["latitude"] is None:
        return CapabilityUnavailable(
            available=False, capability="fare",
            reason="pickup/dropoff area has no resolvable coordinates for this city",
        )
    distance = model_service._haversine_miles(
        (pickup["latitude"], pickup["longitude"]), (dropoff["latitude"], dropoff["longitude"])
    )
    result = pricing_engine.estimate_tariff_base_fare(city_id, distance, hour)
    if result.value is None:
        return CapabilityUnavailable(available=False, capability="fare", reason=result.reason)
    return _envelope(
        city_id, pickup_area_id, dropoff_area_id, "fare", result.value, result.method,
        basis="modeled_estimate", reason=result.reason,
    )


def forecast(city_id: str, metric: str, hours: int = 24) -> ForecastEnvelope | CapabilityUnavailable:
    logger.info("prediction_service.forecast step=start city_id={} metric={} hours={}", city_id, metric, hours)
    _require_city(city_id)
    if not (1 <= hours <= 24):
        raise DomainError(ErrorCode.INVALID_TIME_RANGE, "hours must be between 1 and 24", 400)
    if metric not in _FORECASTABLE_METRICS or models_registry.resolve_model(city_id, metric) is None:
        logger.info("prediction_service.forecast step=capability_unavailable city_id={} metric={}", city_id, metric)
        return CapabilityUnavailable(available=False, capability=metric, reason=f"no active {metric} model for city_id={city_id!r}")

    datasource = get_datasource(city_id)
    if datasource is None:
        logger.warning("prediction_service.forecast step=no_datasource city_id={}", city_id)
        raise DomainError(ErrorCode.DATA_UNAVAILABLE, f"no data source registered for city_id={city_id!r}", 404)

    rows = datasource.get_temporal_metrics(metric)[:hours]
    model_row = models_registry.resolve_model(city_id, metric)
    return ForecastEnvelope(
        city_id=city_id,
        metric=metric,
        model=model_row["model_id"] if model_row else "historical_aggregate",
        model_version=(model_row or {}).get("version"),
        generated_at=datetime.now(timezone.utc),
        source="historical hourly aggregate from the mart (not a forward time-series forecast)",
        series=[ForecastPoint(hour=int(r["hour"]), value=round(float(r["value"]), 2)) for r in rows],
    )
