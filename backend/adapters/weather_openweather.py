"""Real weather adjustment via OpenWeatherMap's free tier (ADR-008).

Free tier has no 2024 historical backfill, so this can only ever be a
capped request-time adjustment on top of the historically-trained fare/demand
predictions -- never a retrainable model feature. `basis="unavailable"` (not
a fabricated "clear" default) when `OPENWEATHER_API_KEY` isn't configured or
the call fails -- this repo has $0 committed budget, so an unconfigured key
is the expected default state, not an error.
"""
from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache

import httpx

from backend.predictors.base import PredictionResult

_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
_URL = "https://api.openweathermap.org/data/2.5/weather"

# Condition codes -> a 0 (mild) - 1 (severe) severity score used as the
# pricing/congestion adjustment input. Grouped by OpenWeatherMap's own
# documented condition-code families (https://openweathermap.org/weather-conditions).
_SEVERITY_BY_GROUP = {
    "Thunderstorm": 0.9,
    "Snow": 0.8,
    "Rain": 0.5,
    "Drizzle": 0.3,
    "Atmosphere": 0.4,  # fog, haze, dust, etc.
    "Clouds": 0.1,
    "Clear": 0.0,
}


@lru_cache(maxsize=256)
def _cached_fetch(lat_bucket: float, lon_bucket: float, hour_bucket: int) -> PredictionResult:
    # ponytail: single-process in-memory cache, not shared across replicas --
    # fine because Infrastructure.md's deployment target is a single
    # free-tier host, not a fleet. Upgrade path is Redis only if that changes.
    if not _API_KEY:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="openweathermap",
            reason="OPENWEATHER_API_KEY not configured",
        )
    try:
        resp = httpx.get(
            _URL,
            params={"lat": lat_bucket, "lon": lon_bucket, "appid": _API_KEY, "units": "metric"},
            timeout=3.0,
        )
        resp.raise_for_status()
        data = resp.json()
        group = data["weather"][0]["main"]
        severity = _SEVERITY_BY_GROUP.get(group, 0.2)
        return PredictionResult(
            value=round(severity, 2), unit="severity_0_to_1", basis="computed",
            source="openweathermap", reason=None,
        )
    except Exception as exc:  # noqa: BLE001 -- any network/API failure degrades honestly
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="openweathermap",
            reason=f"openweathermap request failed: {exc}",
        )


def fetch(lat: float, lon: float, at: datetime) -> PredictionResult:
    # Bucket to ~11km / 30-minute resolution so nearby requests in the same
    # half-hour share one upstream call instead of hammering the free tier.
    bucket_hour = at.replace(minute=(at.minute // 30) * 30, second=0, microsecond=0)
    return _cached_fetch(round(lat, 1), round(lon, 1), int(bucket_hour.timestamp() // 1800))
