"""Shared types for the journey predictor pipeline (ADR-007).

`basis` is structural, not a comment convention: every prediction the
`/journey/estimate` endpoint returns carries one of three honest states --
`computed` (a real algorithm/model/deterministic formula ran),
`modeled_estimate` (a proxy-based guess, never presented as measured fact --
e.g. Ride Availability, Surge Risk), or `unavailable` (no data source exists
yet, `reason` says why). This makes rules.md rule 2 ("never fabricate
results") a type-level property of the response instead of a discipline
every new predictor has to remember on its own.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

Basis = Literal["computed", "modeled_estimate", "unavailable"]


@dataclass
class PredictionResult:
    value: float | str | None
    unit: str | None
    basis: Basis
    source: str
    reason: str | None = None
    # Real min/max date the underlying mart covers (model_service.data_vintage),
    # set only on fields backed by a trained NYC/London model -- so nothing
    # from a 2024/2026-dated warehouse ever claims to be more current than it is.
    data_vintage: str | None = None

    def __post_init__(self) -> None:
        if self.basis != "computed" and not self.reason:
            raise ValueError(f"reason is required when basis={self.basis!r} (source={self.source!r})")


@dataclass
class VehicleProfile:
    vehicle_class: str
    capacity: int
    base_fare_factor: float
    distance_rate_factor: float
    time_rate_factor: float
    minimum_fare_factor: float
    traffic_sensitivity: float
    demand_sensitivity: float
    availability_prior: float
    emission_factor: float
    comfort_score: float


@dataclass
class JourneyContext:
    """Raw inputs plus whatever the adapters (backend/adapters/) returned,
    unprocessed. Never consumed by predictors directly -- see JourneyFeatures."""

    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    departure_time: datetime
    vehicle_type: str
    pickup_zone_id: int | None
    dropoff_zone_id: int | None
    vehicle_profile: VehicleProfile | None
    weather: PredictionResult
    holiday: PredictionResult
    city_id: str = "nyc"


@dataclass
class JourneyFeatures:
    """Derived, named scores every predictor actually consumes. Adding a new
    adapter/data source means adding a field here, never touching every
    predictor's signature."""

    distance_miles: PredictionResult
    duration_min: PredictionResult
    weather_score: PredictionResult
    holiday_score: PredictionResult
    historical_traffic_score: PredictionResult
    vehicle_profile: VehicleProfile | None


class Predictor(Protocol):
    def __call__(self, ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult: ...
