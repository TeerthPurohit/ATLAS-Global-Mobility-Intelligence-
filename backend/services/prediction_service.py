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

import logging
from datetime import datetime, timezone

from backend.datasources import get_datasource
from backend.errors import DomainError
from backend.registry import cities as cities_registry
from backend.registry import models as models_registry
from backend.schemas import (
    CapabilityUnavailable,
    ErrorCode,
    ForecastEnvelope,
    ForecastPoint,
    PredictionEnvelope,
)
from backend.services import model_service

logger = logging.getLogger(__name__)

_FORECASTABLE_METRICS = ("demand", "fare")


def _require_city(city_id: str) -> dict:
    city = cities_registry.get_city(city_id)
    if city is None:
        logger.info("prediction_service: city_id=%s not found", city_id)
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return city


def _envelope(city_id: str, area_id: int | None, dropoff_area_id: int | None, metric: str, value: float, model_name: str) -> PredictionEnvelope:
    model_meta = models_registry.get_model(model_name)
    logger.info("prediction_service: resolved model=%s for city_id=%s metric=%s", model_name, city_id, metric)
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
    )


def predict_demand(city_id: str, area_id: int, hour: int, day_of_week: int) -> PredictionEnvelope | CapabilityUnavailable:
    _require_city(city_id)
    if models_registry.resolve_model(city_id, "demand") is None:
        logger.info("prediction_service: demand capability unavailable for city_id=%s", city_id)
        return CapabilityUnavailable(available=False, capability="demand", reason=f"no active demand model for city_id={city_id!r}")
    try:
        value, model_name = model_service.predict_demand(area_id, hour, day_of_week)
    except KeyError as exc:
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    return _envelope(city_id, area_id, None, "demand", value, model_name)


def predict_fare(city_id: str, pickup_area_id: int, dropoff_area_id: int, hour: int) -> PredictionEnvelope | CapabilityUnavailable:
    _require_city(city_id)
    if models_registry.resolve_model(city_id, "fare") is None:
        logger.info("prediction_service: fare capability unavailable for city_id=%s", city_id)
        return CapabilityUnavailable(available=False, capability="fare", reason=f"no active fare model for city_id={city_id!r}")
    try:
        value, model_name = model_service.predict_fare(pickup_area_id, dropoff_area_id, hour)
    except KeyError as exc:
        raise DomainError(ErrorCode.PREDICTION_FAILED, str(exc), 400) from exc
    return _envelope(city_id, pickup_area_id, dropoff_area_id, "fare", value, model_name)


def forecast(city_id: str, metric: str, hours: int = 24) -> ForecastEnvelope | CapabilityUnavailable:
    _require_city(city_id)
    if not (1 <= hours <= 24):
        raise DomainError(ErrorCode.INVALID_TIME_RANGE, "hours must be between 1 and 24", 400)
    if metric not in _FORECASTABLE_METRICS or models_registry.resolve_model(city_id, metric) is None:
        return CapabilityUnavailable(available=False, capability=metric, reason=f"no active {metric} model for city_id={city_id!r}")

    datasource = get_datasource(city_id)
    if datasource is None:
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
