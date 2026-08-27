"""Prediction orchestrator (SPEC-013 FR-7): check capability against the
registered city row -> resolve model via `model_registry` -> call the
existing, UNCHANGED `model_service.py` functions -> wrap the result in a
provenance envelope. This is a thin orchestration layer, not a second
prediction implementation -- every number it returns is exactly what
`model_service.py` already computed (rule 8: no new inference/training path).

A capability that genuinely isn't wired returns a `CapabilityUnavailable`
200 body (never a fabricated number, matching the `/journey/estimate` "data
unavailable != 4xx for a well-formed request" precedent). A missing area, or
a real failure resolving a known-valid request (e.g. an unrecognized
area_id), raises `DomainError` -- the router translates that to a 404/400
`ErrorResponse`.
"""
from __future__ import annotations  # noqa: I001

from datetime import datetime, timezone

from loguru import logger

from backend.datasources import get_datasource
from backend.errors import DomainError
from backend.registry import CITY_ID
from backend.registry import models as models_registry
from backend.schemas import (
    CapabilityUnavailable,
    ErrorCode,
    ForecastEnvelope,
    ForecastPoint,
    PredictionEnvelope,
)
from backend.registry import cities as cities_registry
from backend.services import geography_service, model_service, pricing_engine, tariff_profiles

_FORECASTABLE_METRICS = ("demand", "fare")


def _require_city() -> dict:
    """The registered city row (ADR-011/013). Absent only if the `cities`
    seed itself is missing -- a deployment fault, surfaced rather than
    papered over with a fabricated profile."""
    profile = cities_registry.get_city_profile()
    if profile is None:
        logger.info("prediction_service._require_city step=not_resolvable")
        raise DomainError(ErrorCode.CITY_NOT_FOUND, "no registered city row", 404)
    return profile


def _envelope(
    area_id: int | None, dropoff_area_id: int | None, metric: str,
    value: float, model_name: str, basis: str = "computed", reason: str | None = None,
) -> PredictionEnvelope:
    model_meta = models_registry.get_model(model_name)
    logger.info("prediction_service._envelope step=model_resolved model={} metric={} basis={}", model_name, metric, basis)
    return PredictionEnvelope(
        city_id=CITY_ID,
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


def predict_demand(area_id: int, hour: int, day_of_week: int) -> PredictionEnvelope | CapabilityUnavailable:
    logger.info("prediction_service.predict_demand step=start area_id={} hour={}", area_id, hour)
    _require_city()
    if models_registry.resolve_model("demand") is None:
        logger.info("prediction_service.predict_demand step=capability_unavailable reason=no_model")
        return CapabilityUnavailable(
            available=False, capability="demand", reason="no active demand model",
        )
    try:
        value, model_name = model_service.predict_demand(area_id, hour, day_of_week)
    except KeyError as exc:
        logger.info("prediction_service.predict_demand step=model_service.predict_demand failed reason={}", exc)
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    return _envelope(area_id, None, "demand", value, model_name, basis="computed")


def predict_fare(pickup_area_id: int, dropoff_area_id: int, hour: int) -> PredictionEnvelope | CapabilityUnavailable:
    logger.info("prediction_service.predict_fare step=start pickup_area_id={} dropoff_area_id={}", pickup_area_id, dropoff_area_id)
    _require_city()
    if models_registry.resolve_model("fare") is not None:
        try:
            value, model_name = model_service.predict_fare(pickup_area_id, dropoff_area_id, hour)
        except KeyError as exc:
            logger.info("prediction_service.predict_fare step=model_service.predict_fare failed reason={}", exc)
            raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
        return _envelope(pickup_area_id, dropoff_area_id, "fare", value, model_name, basis="computed")

    # No trained fare model -- fall through to the tariff-profile estimate,
    # the same source cities.py's capability matrix promises via
    # `fare = has_fare_model or has_tariff`.
    if tariff_profiles.get() is None:
        logger.info("prediction_service.predict_fare step=capability_unavailable reason=no_model_no_tariff")
        return CapabilityUnavailable(
            available=False, capability="fare",
            reason="no active fare model and no tariff profile",
        )
    pickup = geography_service.get_area(pickup_area_id)
    dropoff = geography_service.get_area(dropoff_area_id)
    if not pickup or not dropoff or pickup["latitude"] is None or dropoff["latitude"] is None:
        return CapabilityUnavailable(
            available=False, capability="fare",
            reason="pickup/dropoff area has no resolvable coordinates",
        )
    distance = model_service._haversine_miles(
        (pickup["latitude"], pickup["longitude"]), (dropoff["latitude"], dropoff["longitude"])
    )
    result = pricing_engine.estimate_tariff_base_fare(distance, hour)
    if result.value is None:
        return CapabilityUnavailable(available=False, capability="fare", reason=result.reason)
    return _envelope(
        pickup_area_id, dropoff_area_id, "fare", result.value, result.method,
        basis="modeled_estimate", reason=result.reason,
    )


def forecast(metric: str, hours: int = 24) -> ForecastEnvelope | CapabilityUnavailable:
    logger.info("prediction_service.forecast step=start metric={} hours={}", metric, hours)
    _require_city()
    if not (1 <= hours <= 24):
        raise DomainError(ErrorCode.INVALID_TIME_RANGE, "hours must be between 1 and 24", 400)
    if metric not in _FORECASTABLE_METRICS or models_registry.resolve_model(metric) is None:
        logger.info("prediction_service.forecast step=capability_unavailable metric={}", metric)
        return CapabilityUnavailable(available=False, capability=metric, reason=f"no active {metric} model")

    datasource = get_datasource()
    if datasource is None:
        logger.warning("prediction_service.forecast step=no_datasource")
        raise DomainError(ErrorCode.DATA_UNAVAILABLE, "no data source registered", 404)

    rows = datasource.get_temporal_metrics(metric)[:hours]
    model_row = models_registry.resolve_model(metric)
    return ForecastEnvelope(
        city_id=CITY_ID,
        metric=metric,
        model=model_row["model_id"] if model_row else "historical_aggregate",
        model_version=(model_row or {}).get("version"),
        generated_at=datetime.now(timezone.utc),
        source="historical hourly aggregate from the mart (not a forward time-series forecast)",
        series=[ForecastPoint(hour=int(r["hour"]), value=round(float(r["value"]), 2)) for r in rows],
    )
