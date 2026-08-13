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
    data_vintage: str | None = None
    value_usd: float | None = None
    # Per-component provenance (mirrors PredictionResult): `confidence` is
    # 0-1 and always 0.0 when basis == "unavailable"; `method` names how the
    # number was produced ("trained_fare_model", "tariff_profile_linear",
    # "population_scaling", ...). Both optional -- additive, no client breaks.
    confidence: float | None = None
    method: str | None = None

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
    # Explicit city (registered id, GeoNames id, or free-text place name).
    # Omit only for NYC/London -- auto-detected from pickup coordinates for
    # backward compatibility; every other city must be named explicitly
    # (see journey_service._resolve_city_id).
    city_id: str | None = None


class JourneyHistoryEntry(BaseModel):
    """One row of the prediction log, as the frontend JourneyHistoryEntry
    contract expects it: the log's real columns, `response_json` still the
    serialized JourneyEstimate string it was stored as."""

    id: int
    requested_at: str
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    departure_time: str
    vehicle_type: str
    fare_value: str | None = None
    fare_basis: str | None = None
    confidence_value: float | None = None
    response_json: str
    city_id: str | None = None


class CityJourneyRequest(BaseModel):
    """City-scoped journey estimate request -- deliberately smaller than
    JourneyRequest (no vehicle_type): this endpoint works for any resolvable
    city, not just NYC's vehicle-profile-aware pipeline."""

    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    departure_time: datetime


class CityJourneyEstimate(BaseModel):
    """Deliberately a 4-field subset of JourneyEstimate: distance/duration
    (real, via OSRM, for any city on Earth) plus demand/fare (computed for
    NYC/London where a real model exists, modeled_estimate everywhere else).
    Reusing the full 11-field JourneyEstimate here would force most fields to
    `unavailable` for every non-NYC city -- noisy, not what "any resolvable
    city gets a real answer" means."""

    city_id: str
    distance: PredictionOut
    duration: PredictionOut
    demand: PredictionOut
    fare: PredictionOut
    mode: Literal["zone_enriched", "osrm_only"]


class JourneyEstimate(BaseModel):
    city_id: str
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
    route: Literal["numeric", "explanatory"]
    sql: str | None = None
    session_id: str
    city_id: str | None = None
    area_id: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
    route: Literal["numeric", "explanatory"] | None = None
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
    latitude: float | None = 0.0
    longitude: float | None = 0.0
    timezone: str | None = "UTC"
    currency: str | None = "USD"
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
    transit_coverage: bool = False
    chat_tier: Literal["full_rag", "sql_only", "context_only"] = "context_only"
    # Per-journey-field support (registry.cities.capability_matrix) -- true
    # only where a real model, tariff profile, or covariate actually backs
    # the field for THIS city. Defaults keep older callers working.
    routing: bool = False
    congestion: bool = False
    availability: bool = False
    surge: bool = False
    carbon: bool = False
    best_departure: bool = False


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
    basis: Literal["computed", "modeled_estimate"] = "computed"
    reason: str | None = None


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


# ── Shared Request/Response Schemas for Granular Mobility APIs ─────────────────


class Coordinates(BaseModel):
    """Reusable coordinate pair for any mobility request."""
    lat: float
    lon: float


class JourneyContextRequest(BaseModel):
    """Shared context for all mobility predictions - city, coordinates, time, vehicle."""
    city_id: str
    pickup: Coordinates
    dropoff: Coordinates
    departure_time: datetime
    vehicle_type: str = "car"


class RouteRequest(JourneyContextRequest):
    """Request for routing - inherits all context fields."""
    pass


class PredictionRequest(JourneyContextRequest):
    """Request for fare/demand/congestion/etc predictions - inherits all context fields.

    Optional route information can be provided to avoid recomputing the route.
    """
    distance_km: float | None = None
    duration_min: float | None = None


class CityRequest(BaseModel):
    """Minimal city-scoped request."""
    city_id: str


class MobilityResponse(BaseModel):
    """Base response for all mobility predictions with provenance."""
    value: float | None = None
    unit: str | None = None
    status: Literal["computed", "modeled_estimate", "unavailable"]
    method: str
    source: str
    confidence: float
    reason: str | None = None


class RouteResponse(BaseModel):
    """Route response with distance and duration."""
    distance: MobilityResponse
    duration: MobilityResponse
    request_id: str | None = None
    timestamp: datetime | None = None


class FareBreakdown(BaseModel):
    """Fare breakdown - only includes components actually calculated."""
    base: float | None = None
    distance: float | None = None
    duration: float | None = None
    fees: float | None = None
    surge: float | None = None
    total: float | None = None


class FareResponse(BaseModel):
    """Fare response with breakdown."""
    fare: MobilityResponse
    breakdown: FareBreakdown
    currency: str
    request_id: str | None = None
    timestamp: datetime | None = None


class DemandResponse(BaseModel):
    """Demand response."""
    demand: MobilityResponse
    request_id: str | None = None
    timestamp: datetime | None = None


class CongestionResponse(BaseModel):
    """Congestion response."""
    congestion: MobilityResponse
    request_id: str | None = None
    timestamp: datetime | None = None


class AvailabilityResponse(BaseModel):
    """Availability response."""
    availability: MobilityResponse
    request_id: str | None = None
    timestamp: datetime | None = None


class SurgeResponse(BaseModel):
    """Surge response."""
    surge: MobilityResponse
    request_id: str | None = None
    timestamp: datetime | None = None


class CarbonResponse(BaseModel):
    """Carbon response."""
    carbon: MobilityResponse
    request_id: str | None = None
    timestamp: datetime | None = None


class DepartureTimeResponse(BaseModel):
    """Best departure time response."""
    recommended_departure: str | None = None
    reason: str | None = None
    confidence: float
    status: Literal["computed", "modeled_estimate", "unavailable"]
    request_id: str | None = None
    timestamp: datetime | None = None


class WeatherResponse(BaseModel):
    """Weather context response.

    `severity` is the real 0-1 weather severity score the adapter computes
    (precipitation-driven, with an extreme-temperature bump) -- the only
    weather number this backend actually produces. `temperature` stays None
    (the adapter never returns one); callers must not read it as live
    temperature.
    """
    temperature: float | None = None
    humidity: float | None = None
    precipitation: float | None = None
    wind_speed: float | None = None
    weather_condition: str | None = None
    severity: float | None = None
    source: str
    timestamp: datetime
    city_id: str


class HolidayResponse(BaseModel):
    """Holiday context response."""
    is_holiday: bool
    holiday_name: str | None = None
    country: str
    date: str
    source: str


class TrafficResponse(BaseModel):
    """Traffic context response - only what's actually available."""
    congestion_level: float | None = None
    source: str
    is_live: bool = False
    timestamp: datetime
    city_id: str
    note: str | None = None


class CitySearchRequest(BaseModel):
    """City search parameters."""
    q: str | None = None
    country: str | None = None
    tier: str | None = None
    supported: bool | None = None
    page: int = 1
    limit: int = 50


class CitySearchResponse(BaseModel):
    """City search response."""
    results: list[City]
    total: int
    page: int
    limit: int


class CityProfileResponse(BaseModel):
    """Complete city profile response."""
    id: str
    name: str
    country_code: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    currency: str
    tier: str
    population: int | None = None
    model_status: str
    data_source: str
    geography_type: str
    mobility_mode: str
    confidence: float
    data_availability: dict[str, bool]


class CityCapabilitiesResponse(BaseModel):
    """City capabilities response."""
    city_id: str
    capabilities: dict[str, bool]


class CityTariffResponse(BaseModel):
    """City tariff response."""
    available: bool
    city_id: str
    reason: str | None = None
    # When available, includes all tariff profile fields
    currency: str | None = None
    base_fare: float | None = None
    per_km: float | None = None
    per_min: float | None = None
    min_fare: float | None = None
    night_multiplier: float | None = None
    airport_surcharge: float | None = None
    booking_fee: float | None = None
    platform_fee: float | None = None
    tolls: float | None = None
    peak_multiplier: float | None = None
    vehicle_multiplier: float | None = None
    surge_multiplier: float | None = None
    effective_from: str | None = None
    version: str | None = None
    source_type: str | None = None
    confidence: float | None = None
    notes: str | None = None
    generated_at: str | None = None
    model_id: str | None = None


class CityZonesResponse(BaseModel):
    """City zones response."""
    available: bool
    city_id: str
    reason: str | None = None
    zones: list[Zone] | None = None


class SystemHealthResponse(BaseModel):
    """System health response."""
    status: str
    warehouse: str
    models: str
    timestamp: datetime


class SystemCapabilitiesResponse(BaseModel):
    """System-wide capabilities response."""
    total_cities: int
    capabilities: dict[str, dict[str, int]]


class SystemModelsResponse(BaseModel):
    """System models response."""
    models: list[dict]


class SystemPipelineStatusResponse(BaseModel):
    """System pipeline status response."""
    status: str
    last_run: str | None = None
    details: dict | None = None


class AnalyticsSummaryResponse(BaseModel):
    """Analytics summary response."""
    total_predictions: int
    cities_served: int
    date_range: dict[str, str | None]
    top_cities: list[dict]


class AnalyticsInsightsResponse(BaseModel):
    """Analytics insights response."""
    insights: list[dict]


class AnalyticsHistoryResponse(BaseModel):
    """Analytics history response."""
    history: list[dict]
    limit: int
    offset: int


class AnalyticsTrendsResponse(BaseModel):
    """Analytics trends response."""
    trends: dict[str, list[float]]
    period: str
