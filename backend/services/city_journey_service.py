"""City-scoped journey estimate (distance/duration/demand/fare) for any
resolvable city -- not just NYC's full 11-field vehicle-profile pipeline
(journey_service.py, left untouched, still NYC-only by design).

OSRM (backend/adapters/routing_osrm.py) already returns real, worldwide
`basis="computed"` route distance/duration -- this module is what makes that
reachable outside the NYC-only pipeline. Demand/fare use a real trained model
for nyc/london where one exists, and fall back to the honestly-labeled
cross-city estimates (backend/services/estimation_service.py) everywhere
else -- never a bare `unavailable` once a route resolves, since a real
distance is always available at that point.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.adapters import routing_osrm  # noqa: E402
from backend.errors import DomainError  # noqa: E402
from backend.predictors.base import PredictionResult  # noqa: E402
from backend.registry import models as models_registry  # noqa: E402
from backend.schemas import CityJourneyEstimate, ErrorCode, PredictionOut  # noqa: E402
from backend.services import estimation_service, geography_service, global_geography_service, model_service, prediction_service  # noqa: E402

logger = logging.getLogger(__name__)

_ZONE_ENRICHED_CITIES = ("nyc", "london")


def _to_out(result: PredictionResult) -> PredictionOut:
    return PredictionOut(value=result.value, unit=result.unit, basis=result.basis, source=result.source, reason=result.reason)


def _require_resolvable_city(city_id: str) -> dict:
    profile = global_geography_service.get_city_profile(city_id)
    if profile is None:
        raise DomainError(ErrorCode.CITY_NOT_FOUND, f"unknown city_id={city_id!r}", 404)
    return profile


def _distance_and_duration(pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float) -> tuple[PredictionResult, PredictionResult]:
    distance = routing_osrm.fetch_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    duration = routing_osrm.fetch_duration(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    if distance.basis == "unavailable":
        miles = model_service.haversine_miles((pickup_lat, pickup_lon), (dropoff_lat, dropoff_lon))
        distance = PredictionResult(
            value=round(miles, 2), unit="miles", basis="computed", source="haversine",
            reason=None,
        )
    return distance, duration


def _demand_and_fare_zone_enriched(
    city_id: str, pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    hour: int, day_of_week: int, distance: PredictionResult, country_code: str | None,
) -> tuple[PredictionResult, PredictionResult]:
    pickup_area_id = geography_service.resolve_for_city(city_id, pickup_lat, pickup_lon)
    dropoff_area_id = geography_service.resolve_for_city(city_id, dropoff_lat, dropoff_lon)

    if pickup_area_id is None:
        demand = PredictionResult(
            value=None, unit=None, basis="unavailable", source="demand",
            reason=f"pickup point outside {city_id}'s known area coverage",
        )
    else:
        envelope = prediction_service.predict_demand(city_id, pickup_area_id, hour, day_of_week)
        if hasattr(envelope, "prediction"):  # PredictionEnvelope
            demand = PredictionResult(value=envelope.prediction, unit="trips", basis=envelope.basis, source=envelope.model, reason=None)
        else:  # CapabilityUnavailable
            demand = PredictionResult(value=None, unit=None, basis="unavailable", source="demand", reason=envelope.reason)

    if pickup_area_id is not None and dropoff_area_id is not None and models_registry.resolve_model(city_id, "fare") is not None:
        fare_envelope = prediction_service.predict_fare(city_id, pickup_area_id, dropoff_area_id, hour)
        if hasattr(fare_envelope, "prediction"):  # PredictionEnvelope
            fare = PredictionResult(value=fare_envelope.prediction, unit="usd", basis=fare_envelope.basis, source=fare_envelope.model, reason=None)
        else:
            fare = PredictionResult(value=None, unit=None, basis="unavailable", source="fare", reason=fare_envelope.reason)
    else:
        # No trained fare model for this city (or a point fell outside zone
        # coverage) -- fall back to the same PPP-adjusted estimate used for
        # any other city, rather than a bare unavailable.
        fare = estimation_service.estimate_fare_per_mile(country_code)
        if fare.basis == "modeled_estimate" and distance.value is not None:
            fare = PredictionResult(
                value=round(fare.value * distance.value, 2), unit="usd", basis="modeled_estimate",
                source=fare.source, reason=fare.reason,
            )
    return demand, fare


def _demand_and_fare_estimate_only(
    city_id: str, population: int | None, distance: PredictionResult, country_code: str | None,
    pickup_lat: float, pickup_lon: float, departure_time,
) -> tuple[PredictionResult, PredictionResult]:
    if population is None:
        demand = PredictionResult(value=None, unit=None, basis="unavailable", source="cross_city_estimation", reason="no population covariate resolvable for this location")
    else:
        demand = estimation_service.estimate_city_demand(city_id, population, lat=pickup_lat, lon=pickup_lon, at=departure_time)

    fare = estimation_service.estimate_fare_per_mile(country_code)
    if fare.basis == "modeled_estimate" and distance.value is not None:
        fare = PredictionResult(
            value=round(fare.value * distance.value, 2), unit="usd", basis="modeled_estimate",
            source=fare.source, reason=fare.reason,
        )
    return demand, fare


def estimate(city_id: str, pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float, departure_time) -> CityJourneyEstimate:
    profile = _require_resolvable_city(city_id)
    distance, duration = _distance_and_duration(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    country_code = profile.get("country_code")

    if city_id in _ZONE_ENRICHED_CITIES:
        demand, fare = _demand_and_fare_zone_enriched(
            city_id, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
            departure_time.hour, departure_time.weekday(), distance, country_code,
        )
        mode = "zone_enriched"
    else:
        demand, fare = _demand_and_fare_estimate_only(
            city_id, profile.get("population"), distance, country_code, pickup_lat, pickup_lon, departure_time,
        )
        mode = "osrm_only"

    logger.info("city_journey_service: city_id=%s mode=%s distance_basis=%s demand_basis=%s fare_basis=%s", city_id, mode, distance.basis, demand.basis, fare.basis)
    return CityJourneyEstimate(
        city_id=city_id, distance=_to_out(distance), duration=_to_out(duration),
        demand=_to_out(demand), fare=_to_out(fare), mode=mode,
    )
