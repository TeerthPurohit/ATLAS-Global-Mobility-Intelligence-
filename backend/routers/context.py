"""Context APIs - Weather, Holiday, Traffic (Part 3 of API Decomposition).

Environmental/context information separated from mobility predictions.
`lat`/`lon` are optional: omitted, they fall back to the served city's own
seeded coordinates. A registry with no city row is a 400, never a bare 500.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

# Add repo root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.adapters import holidays_nager, routing_osrm, weather_openmeteo  # noqa: E402
from backend.predictors import journey_predictors  # noqa: E402
from backend.predictors.base import JourneyContext, PredictionResult  # noqa: E402
from backend.schemas import HolidayResponse, TrafficResponse, WeatherResponse  # noqa: E402
from backend.registry import CITY_ID  # noqa: E402
from backend.registry import cities as cities_registry  # noqa: E402
from backend.services import journey_service  # noqa: E402

router = APIRouter(prefix="/api/context", tags=["Context"])


def _city_coords() -> tuple[float, float]:
    """The served city's seeded (lat, lon). Raises 400 -- not a bare 500 --
    when the registry has no row or the row carries no coordinates.

    Reads `profile["coordinates"]`, which is where `get_city_profile()`
    actually nests them; the previous top-level `profile.get("latitude")`
    always read None, so this fallback never fired before.
    """
    profile = cities_registry.get_city_profile()
    if not profile:
        raise HTTPException(status_code=400, detail="Cannot resolve coordinates: no registered city")
    coords = profile.get("coordinates") or {}
    lat, lon = coords.get("latitude"), coords.get("longitude")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="City profile is missing coordinates")
    return float(lat), float(lon)


@router.get("/weather", response_model=WeatherResponse)
def weather(
    lat: float | None = Query(None, description="Latitude; defaults to the city centroid"),
    lon: float | None = Query(None, description="Longitude; defaults to the city centroid"),
    timestamp: str | None = Query(None, description="ISO timestamp, defaults to now"),
) -> WeatherResponse:
    """Get weather at a specific time.

    Reports the adapter's real 0-1 weather severity score under `severity`;
    `temperature` is always None because no adapter here returns one (see
    WeatherResponse docstring).
    """
    logger.info("GET /api/context/weather step=start lat={} lon={} timestamp={}", lat, lon, timestamp)
    if lat is None or lon is None:
        lat, lon = _city_coords()

    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("GET /api/context/weather step=invalid_timestamp value={!r}", timestamp)
            raise HTTPException(status_code=400, detail=f"invalid timestamp={timestamp!r}: expected ISO 8601")
    else:
        dt = datetime.now()

    weather_result = weather_openmeteo.fetch(lat, lon, dt)
    logger.info("GET /api/context/weather step=done source={}", weather_result.source)

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
        city_id=CITY_ID,
    )


@router.get("/holiday", response_model=HolidayResponse)
def holiday(
    lat: float | None = Query(None, description="Latitude; defaults to the city centroid"),
    lon: float | None = Query(None, description="Longitude; defaults to the city centroid"),
    date: str | None = Query(None, description="ISO date (YYYY-MM-DD), defaults to today"),
) -> HolidayResponse:
    """Check if a date is a holiday in the city's country."""
    logger.info("GET /api/context/holiday step=start lat={} lon={} date={}", lat, lon, date)
    if lat is None or lon is None:
        lat, lon = _city_coords()

    if date:
        try:
            dt = datetime.fromisoformat(date)
        except ValueError:
            logger.warning("GET /api/context/holiday step=invalid_date value={!r}", date)
            raise HTTPException(status_code=400, detail=f"invalid date={date!r}: expected YYYY-MM-DD")
    else:
        dt = datetime.now()

    holiday_result = holidays_nager.fetch(lat, lon, dt)
    logger.info("GET /api/context/holiday step=done source={}", holiday_result.source)

    is_holiday = holiday_result.value == 1.0 if holiday_result.value is not None else False
    holiday_name = holiday_result.reason if is_holiday and holiday_result.reason else None

    country = (cities_registry.get_city_profile() or {}).get("country_code") or "XX"

    return HolidayResponse(
        is_holiday=is_holiday,
        holiday_name=holiday_name,
        country=country,
        date=dt.date().isoformat(),
        source=holiday_result.source,
    )


@router.get("/traffic", response_model=TrafficResponse)
def traffic(
    lat: float | None = Query(None, description="Latitude; defaults to the city centroid"),
    lon: float | None = Query(None, description="Longitude; defaults to the city centroid"),
) -> TrafficResponse:
    """Get traffic/congestion information.

    Returns a historical traffic score where available (zone pairs). Does NOT
    claim real-time traffic - only historical estimates.
    """
    logger.info("GET /api/context/traffic step=start lat={} lon={}", lat, lon)
    if lat is None or lon is None:
        lat, lon = _city_coords()

    dt = datetime.now()
    ctx = journey_service.build_context(lat, lon, lat + 0.01, lon + 0.01, dt, "car")
    features = journey_service.build_features(ctx)

    traffic_score = features.historical_traffic_score
    logger.info("GET /api/context/traffic step=done basis={}", traffic_score.basis)

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
        city_id=CITY_ID,
        note=note,
    )
