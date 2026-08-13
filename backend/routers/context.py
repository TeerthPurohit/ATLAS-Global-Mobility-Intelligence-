"""Context APIs - Weather, Holiday, Traffic (Part 3 of API Decomposition).

Environmental/context information separated from mobility predictions.
An unresolvable city_id is a client error (400), never a bare 500.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

# Add repo root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.adapters import holidays_nager, routing_osrm, weather_openmeteo  # noqa: E402
from backend.predictors import journey_predictors  # noqa: E402
from backend.predictors.base import JourneyContext, PredictionResult  # noqa: E402
from backend.schemas import HolidayResponse, TrafficResponse, WeatherResponse  # noqa: E402
from backend.services import global_geography_service, journey_service  # noqa: E402

router = APIRouter(prefix="/api/context", tags=["Context"])


def _resolve_coords(city_id: str) -> tuple[float, float]:
    """Resolve a city to (lat, lon). Raises 400 -- not a bare 500 -- when the
    city is unknown or has no coordinates."""
    profile = global_geography_service.get_city_profile(city_id)
    if not profile:
        raise HTTPException(status_code=400, detail=f"Cannot resolve coordinates for city_id={city_id}")
    lat = profile.get("latitude")
    lon = profile.get("longitude")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail=f"City profile missing coordinates for {city_id}")
    return float(lat), float(lon)


@router.get("/weather", response_model=WeatherResponse)
def weather(
    city_id: str = Query(..., description="City identifier"),
    lat: float | None = Query(None, description="Latitude (required if city_id not resolvable)"),
    lon: float | None = Query(None, description="Longitude (required if city_id not resolvable)"),
    timestamp: str | None = Query(None, description="ISO timestamp, defaults to now"),
) -> WeatherResponse:
    """Get weather for a city at a specific time.

    Accepts either city_id or lat/lon coordinates. Reports the adapter's real
    0-1 weather severity score under `severity`; `temperature` is always None
    because no adapter here returns one (see WeatherResponse docstring).
    """
    if lat is None or lon is None:
        lat, lon = _resolve_coords(city_id)

    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid timestamp={timestamp!r}: expected ISO 8601")
    else:
        dt = datetime.now()

    weather_result = weather_openmeteo.fetch(lat, lon, dt)

    severity = weather_result.value if weather_result.basis == "computed" else None
    note = None
    if severity is not None:
        note = "0-1 weather severity (precipitation-driven, extreme-temp bump) -- not live temperature"
    elif weather_result.reason:
        note = weather_result.reason

    return WeatherResponse(
        temperature=None,
        humidity=None,  # Open-Meteo adapter doesn't return humidity currently
        precipitation=None,
        wind_speed=None,
        weather_condition=note,
        severity=severity,
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
    profile = None
    if lat is None or lon is None:
        profile = global_geography_service.get_city_profile(city_id)
        if not profile:
            raise HTTPException(status_code=400, detail=f"Cannot resolve coordinates for city_id={city_id}")
        lat = profile.get("latitude")
        lon = profile.get("longitude")
        if lat is None or lon is None:
            raise HTTPException(status_code=400, detail=f"City profile missing coordinates for {city_id}")

    if date:
        try:
            dt = datetime.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid date={date!r}: expected YYYY-MM-DD")
    else:
        dt = datetime.now()

    holiday_result = holidays_nager.fetch(lat, lon, dt)

    is_holiday = holiday_result.value == 1.0 if holiday_result.value is not None else False
    holiday_name = holiday_result.reason if is_holiday and holiday_result.reason else None

    country = (profile or global_geography_service.get_city_profile(city_id) or {}).get("country_code", "XX")

    return HolidayResponse(
        is_holiday=is_holiday,
        holiday_name=holiday_name,
        country=country,
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
    if lat is None or lon is None:
        lat, lon = _resolve_coords(city_id)

    dt = datetime.now()
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
