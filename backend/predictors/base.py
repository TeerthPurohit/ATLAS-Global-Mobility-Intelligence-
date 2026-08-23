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
    # set only on fields backed by a trained model -- so nothing
    # from a 2024/2026-dated warehouse ever claims to be more current than it is.
    data_vintage: str | None = None
    # Per-component provenance, both optional and last in the field order so
    # every existing keyword-only construction site keeps working unchanged
    # (checked: no positional PredictionResult(...) exists in this repo).
    # `confidence` is 0-1, NOT a percentage; `unavailable` is forced to 0.0
    # below so no caller can ever attach a misleadingly nonzero number to a
    # component that has no value. `method` names how the number was produced
    # ("xgboost_fare_v1", "tariff_profile_linear", "population_scaling", ...)
    # -- coarser than `source`, stable enough to group/aggregate on.
    confidence: float | None = None
    method: str | None = None
    # Real 0-1 numeric score behind a categorical `value` bucket (LOW/MEDIUM/
    # HIGH/...). The /api/mobility/* surface needs a number per its response
    # model while /journey/estimate + rag/ keep the categorical `value` as-is
    # (ADR-007), so the predictor computes the score ONCE here and each
    # consumer shapes it. None means "no numeric score exists".
    score: float | None = None

    def __post_init__(self) -> None:
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0,1], got {self.score!r} (source={self.source!r})")
        if self.basis != "computed" and not self.reason:
            raise ValueError(f"reason is required when basis={self.basis!r} (source={self.source!r})")
        if self.basis == "unavailable":
            self.confidence = 0.0
        elif self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence!r} (source={self.source!r})")


# The basis-only weights predict_confidence() has always used. Kept here so a
# per-component `confidence` and the overall figure share one scale.
BASIS_CONFIDENCE: dict[str, float] = {"computed": 1.0, "modeled_estimate": 0.5, "unavailable": 0.0}


def effective_confidence(result: PredictionResult) -> float:
    """A component's own measured/derived confidence when it has one, the
    basis default otherwise -- so adding richer per-component numbers can
    only refine the existing weighting, never silently redefine it."""
    if result.confidence is not None:
        return result.confidence
    return BASIS_CONFIDENCE[result.basis]


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
