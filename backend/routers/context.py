"""Context APIs - Weather, Holiday, Traffic (Part 3 of API Decomposition).

Environmental/context information separated from mobility predictions.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query

# Add repo root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.adapters import holidays_nager, routing_osrm, weather_openmeteo  # noqa: E402
from backend.predictors import journey_predictors  # noqa: E402
from backend.predictors.base import JourneyContext, PredictionResult  # noqa: E402
from backend.schemas import HolidayResponse, TrafficResponse, WeatherResponse  # noqa: E402
from backend.services import global_geography_service, journey_service  # noqa: E402

router = APIRouter(prefix="/api/context", tags=["Context"])


@router.get("/weather", response_model=WeatherResponse)
def weather(
    city_id: str = Query(..., description="City identifier"),
    lat: float | None = Query(None, description="Latitude (required if city_id not resolvable)"),
    lon: float | None = Query(None, description="Longitude (required if city_id not resolvable)"),
    timestamp: str | None = Query(None, description="ISO timestamp, defaults to now"),
) -> WeatherResponse:
    """Get weather for a city at a specific time.

    Accepts either city_id or lat/lon coordinates.
    """
    # Resolve coordinates from city_id if needed
    if lat is None or lon is None:
        profile = global_geography_service.get_city_profile(city_id)
        if not profile:
            raise ValueError(f"Cannot resolve coordinates for city_id={city_id}")
        lat = profile.get("latitude")
        lon = profile.get("longitude")
        if lat is None or lon is None:
            raise ValueError(f"City profile missing coordinates for {city_id}")

    # Parse timestamp
    if timestamp:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    else:
        dt = datetime.utcnow()

    # Fetch weather
    weather_result = weather_openmeteo.fetch(lat, lon, dt)

    return WeatherResponse(
        temperature=weather_result.value if weather_result.value is not None else None,
        humidity=None,  # Open-Meteo adapter doesn't return humidity currently
        precipitation=None,
        wind_speed=None,
        weather_condition=None,
        source=weather_result.source,
        timestamp=dt,
        city_id=city_id,
    )


@router.get("/holiday", response_model=HolidayResponse)
def holiday(
    city_id: str = Query(..., description="City identifier"),
    lat: float | None = Query(None, description="Latitude (required if city_id not resolvable)"),
    lon: float | None = Query(None, description="Longitude (required if city_id not resolvable)"),
    date: str | None = Query(None, description="ISO date (YYYY-MM-DD), defaults to today"),
) -> HolidayResponse:
    """Check if a date is a holiday in the city's country."""
    # Resolve coordinates from city_id if needed
    if lat is None or lon is None:
        profile = global_geography_service.get_city_profile(city_id)
        if not profile:
            raise ValueError(f"Cannot resolve coordinates for city_id={city_id}")
        lat = profile.get("latitude")
        lon = profile.get("longitude")
        if lat is None or lon is None:
            raise ValueError(f"City profile missing coordinates for {city_id}")

    # Parse date
    if date:
        dt = datetime.fromisoformat(date)
    else:
        dt = datetime.utcnow()

    # Fetch holiday info
    holiday_result = holidays_nager.fetch(lat, lon, dt)

    is_holiday = holiday_result.value == 1.0 if holiday_result.value is not None else False
    holiday_name = None
    if is_holiday and holiday_result.reason:
        # Extract holiday name from reason if available
        holiday_name = holiday_result.reason

    return HolidayResponse(
        is_holiday=is_holiday,
        holiday_name=holiday_name,
        country=global_geography_service.get_city_profile(city_id).get("country_code", "XX") if global_geography_service.get_city_profile(city_id) else "XX",
        date=dt.date().isoformat(),
        source=holiday_result.source,
    )


@router.get("/traffic", response_model=TrafficResponse)
def traffic(
    city_id: str = Query(..., description="City identifier"),
    lat: float | None = Query(None, description="Latitude (required if city_id not resolvable)"),
    lon: float | None = Query(None, description="Longitude (required if city_id not resolvable)"),
) -> TrafficResponse:
    """Get traffic/congestion information for a city.

    Returns historical traffic score where available (NYC zone pairs).
    Does NOT claim real-time traffic - only historical estimates.
    """
    # Resolve coordinates from city_id if needed
    if lat is None or lon is None:
        profile = global_geography_service.get_city_profile(city_id)
        if not profile:
            raise ValueError(f"Cannot resolve coordinates for city_id={city_id}")
        lat = profile.get("latitude")
        lon = profile.get("longitude")
        if lat is None or lon is None:
            raise ValueError(f"City profile missing coordinates for {city_id}")

    # For now, build a context to get the historical traffic score
    # This requires a mock dropoff to compute a zone pair
    dt = datetime.utcnow()
    ctx = journey_service.build_context(lat, lon, lat + 0.01, lon + 0.01, dt, "car", city_id)
    features = journey_service.build_features(ctx)

    traffic_score = features.historical_traffic_score

    is_live = False
    congestion_level = None
    note = None

    if traffic_score.basis == "computed" and traffic_score.value is not None:
        congestion_level = traffic_score.value
        note = "Historical traffic score from zone pair flows (not live data)"
    elif traffic_score.basis == "unavailable":
        note = traffic_score.reason or "No historical traffic data available for this location"
    else:
        note = "Traffic estimation method: " + (traffic_score.source or "unknown")

    return TrafficResponse(
        congestion_level=congestion_level,
        source=traffic_score.source,
        is_live=is_live,
        timestamp=dt,
        city_id=city_id,
        note=note,
    )