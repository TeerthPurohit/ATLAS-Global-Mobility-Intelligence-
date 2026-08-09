"""City-scoped journey estimate (distance/duration/demand/fare) -- a thin
4-field view over `journey_service.estimate()` (ADR-011).

Used to duplicate its own PPP-ratio fare estimate; now the same city-aware
engine backs both this endpoint and the full 11-field `/journey/estimate`,
so a Mumbai/Tokyo/Lagos fare here comes from the same `tariff_profiles`-backed
pricing engine (real NYC-fare-anchored, per-city cached), not a separate,
weaker estimate that fails whenever the World Bank PPP API times out.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.errors import DomainError  # noqa: E402
from backend.predictors.base import PredictionResult  # noqa: E402
from backend.schemas import CityJourneyEstimate, ErrorCode, PredictionOut  # noqa: E402
from backend.services import global_geography_service, journey_service  # noqa: E402

logger = logging.getLogger(__name__)

_ZONE_ENRICHED_CITIES = ("nyc", "london")
# Vehicle class used for this endpoint's fare -- "mini" has every
# base_fare_factor/rate multiplier at 1.0 (dbt_project/seeds/vehicle_profiles.csv),
# i.e. no adjustment on top of the base fare, matching this endpoint's
# deliberately vehicle-agnostic 4-field contract.
_DEFAULT_VEHICLE_CLASS = "mini"


def _to_out(pr: PredictionResult) -> PredictionOut:
    return PredictionOut(value=pr.value, unit=pr.unit, basis=pr.basis, source=pr.source, reason=pr.reason, data_vintage=pr.data_vintage)


def estimate(
    city_id: str, pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float, departure_time: datetime,
) -> CityJourneyEstimate:
    if global_geography_service.get_city_profile(city_id) is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)

    components = journey_service.estimate(
        pickup_lat=pickup_lat, pickup_lon=pickup_lon, dropoff_lat=dropoff_lat, dropoff_lon=dropoff_lon,
        departure_time=departure_time, vehicle_type=_DEFAULT_VEHICLE_CLASS, city_id=city_id,
    )
    resolved_city_id = components["city_id"]
    mode = "zone_enriched" if resolved_city_id in _ZONE_ENRICHED_CITIES else "osrm_only"

    logger.info("city_journey_service: city_id=%s mode=%s fare_basis=%s", resolved_city_id, mode, components["fare"].basis)
    return CityJourneyEstimate(
        city_id=resolved_city_id, distance=_to_out(components["distance"]), duration=_to_out(components["duration"]),
        demand=_to_out(components["demand"]), fare=_to_out(components["fare"]), mode=mode,
    )
