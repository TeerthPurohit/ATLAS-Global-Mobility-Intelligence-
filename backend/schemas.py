"""Pydantic request/response models for API routes (FR-7).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class DemandPrediction(BaseModel):
    zone_id: int
    hour: int
    day_of_week: int
    predicted_demand: float
    model: str


class FarePrediction(BaseModel):
    pickup_zone: int
    dropoff_zone: int
    hour: int
    predicted_fare: float
    model: str


class Zone(BaseModel):
    zone_id: int
    zone: str
    borough: str
    service_zone: str | None = None
    latitude: float
    longitude: float


class PredictionOut(BaseModel):
    """Every journey field carries `basis` structurally (ADR-007) -- never a
    bare number pretending to be more certain than it is."""

    value: float | str | None
    unit: str | None
    basis: Literal["computed", "modeled_estimate", "unavailable"]
    source: str
    reason: str | None = None
    ui_label: str | None = None

    def model_post_init(self, __context: typing.Any) -> None:
        if self.ui_label is None:
            if self.basis == "computed":
                self.ui_label = "Model Prediction"
            elif self.basis == "modeled_estimate":
                self.ui_label = "Modeled Estimate"
            else:
                self.ui_label = "Unavailable"


class JourneyRequest(BaseModel):
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    departure_time: datetime
    vehicle_type: str


class JourneyEstimate(BaseModel):
    distance: PredictionOut
    duration: PredictionOut
    fare: PredictionOut
    fare_range: PredictionOut
    demand: PredictionOut
    carbon_emissions: PredictionOut
    congestion: PredictionOut
    ride_availability: PredictionOut
    surge_risk: PredictionOut
    best_departure_time: PredictionOut
    confidence: PredictionOut
    fare_breakdown: dict[str, PredictionOut]
    ai_recommendation: PredictionOut


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    city_id: str | None = None
    area_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    route: str
    sql: str | None = None
    session_id: str
    city_id: str | None = None
    area_id: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
    route: str | None = None
    sql: str | None = None
    timestamp: str


# ── Global Mobility Domain Model (SPEC-013 FR-8/FR-9) ──────────────────────


class ErrorCode(str, Enum):
    CITY_NOT_SUPPORTED = "CITY_NOT_SUPPORTED"
    CITY_NOT_FOUND = "CITY_NOT_FOUND"
    COUNTRY_NOT_SUPPORTED = "COUNTRY_NOT_SUPPORTED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    AREA_NOT_FOUND = "AREA_NOT_FOUND"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
    PREDICTION_FAILED = "PREDICTION_FAILED"
    CHAT_FAILED = "CHAT_FAILED"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Country(BaseModel):
    iso_code: str
    name: str
    supported: bool
    supported_city_count: int


class CountriesResponse(BaseModel):
    countries: list[Country]


class City(BaseModel):
    id: str
    name: str
    country_code: str
    latitude: float
    longitude: float
    timezone: str
    currency: str
    status: str
    data_source: str
    geography_type: str
    mobility_mode: str = "ride_hailing"
    model_status: str
    last_updated: str


class Capabilities(BaseModel):
    mobility_mode: str = "ride_hailing"
    area_type: str = "tlc_zone"
    demand: bool
    fare: bool
    journey: bool
    chat: bool
    area_analysis: bool
    forecast: bool = True


class Area(BaseModel):
    area_id: int
    city_id: str
    name: str
    area_type: str
    parent_area_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class CapabilityUnavailable(BaseModel):
    """200-with-structured-body shape for a well-formed request against a
    real but not-yet-wired capability (API Design table: unsupported
    city/capability returns 200, not a bare error, matching the
    /journey/estimate "data unavailable != 4xx" precedent)."""

    available: Literal[False]
    capability: str
    reason: str


class PredictionEnvelope(BaseModel):
    """Provenance wrapper prediction_service.py returns for every city-scoped
    prediction (SPEC-013 FR-7) -- never a bare number."""

    city_id: str
    area_id: int | None = None
    dropoff_area_id: int | None = None
    metric: str
    prediction: float
    model: str
    model_version: str | None = None
    generated_at: datetime
    data_timestamp: str | None = None
    source: str


class ForecastPoint(BaseModel):
    hour: int
    value: float


class ForecastEnvelope(BaseModel):
    city_id: str
    metric: str
    model: str
    model_version: str | None = None
    generated_at: datetime
    source: str
    series: list[ForecastPoint]


class CityDemandPredictRequest(BaseModel):
    area_id: int
    hour: int
    day_of_week: int


class CityFarePredictRequest(BaseModel):
    pickup_area_id: int
    dropoff_area_id: int
    hour: int
