"""Real weather adjustment via Open-Meteo's free forecast API (ADR-008
update, 2026-08-09) -- no API key required, unlike the OpenWeatherMap
adapter this replaces. Preserves the exact same `PredictionResult(value: 0-1
severity, unit="severity_0_to_1", ...)` contract as `weather_openweather.py`
since existing consumers (`journey_predictors.predict_congestion`,
`pricing_engine._weather_adjustment`) treat `.value` as a direct multiplier
-- returning raw temperature there would silently blow up the fare
adjustment ~20x.

Severity is derived from real temperature/precipitation, not an upstream
condition-code label (Open-Meteo's `forecast` endpoint doesn't return one at
this resolution) -- a documented, hand-picked formula, same "weights are a
product rule, not a measured fact" honesty as the OpenWeatherMap condition
table it replaces:
  - precipitation-dominant: 0mm/hr -> 0, >=7.6mm/hr (NWS "heavy rain"
    threshold) -> 1.0, linear between.
  - a flat +0.3 bump for freezing or extreme heat (icy roads / heat-related
    slowdowns), same spirit as the old table's per-condition weights.

Open-Meteo also has a free keyless historical archive
(archive-api.open-meteo.com/v1/era5) -- see scripts/backfill_weather_openmeteo.py,
which is what actually lifts ADR-008's "weather can never be a retrainable
feature" ceiling; this module is the request-time adapter only.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import httpx
from loguru import logger

from backend.predictors.base import PredictionResult

_URL = "https://api.open-meteo.com/v1/forecast"

_HEAVY_RAIN_MM_PER_HR = 7.6
_FREEZING_C = 0.0
_EXTREME_HEAT_C = 35.0
_TEMP_EXTREME_BUMP = 0.3


def _severity_from_conditions(temp_c: float, precip_mm_hr: float) -> float:
    precip_component = min(1.0, max(0.0, precip_mm_hr) / _HEAVY_RAIN_MM_PER_HR)
    temp_component = _TEMP_EXTREME_BUMP if (temp_c <= _FREEZING_C or temp_c >= _EXTREME_HEAT_C) else 0.0
    return round(min(1.0, precip_component + temp_component), 2)


@lru_cache(maxsize=256)
def _cached_fetch(lat_bucket: float, lon_bucket: float, hour_bucket: int) -> PredictionResult:
    logger.debug("weather_openmeteo step=fetch lat={} lon={}", lat_bucket, lon_bucket)
    try:
        resp = httpx.get(
            _URL,
            params={
                "latitude": lat_bucket, "longitude": lon_bucket,
                "hourly": "temperature_2m,precipitation", "forecast_days": 1,
            },
            timeout=4.0,
        )
        resp.raise_for_status()
        hourly = resp.json()["hourly"]
        temp_c = hourly["temperature_2m"][0]
        precip_mm = hourly["precipitation"][0]
        severity = _severity_from_conditions(temp_c, precip_mm)
        return PredictionResult(
            value=severity, unit="severity_0_to_1", basis="computed", source="open-meteo", reason=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("weather_openmeteo step=fetch failed lat={} lon={} reason={}", lat_bucket, lon_bucket, exc)
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="open-meteo",
            reason=f"open-meteo request failed: {exc}",
        )


def fetch(lat: float, lon: float, at: datetime) -> PredictionResult:
    # Bucket to ~11km / 30-minute resolution, same convention as the adapter
    # this replaces, so nearby requests in the same half-hour share one call.
    bucket_hour = at.replace(minute=(at.minute // 30) * 30, second=0, microsecond=0)
    return _cached_fetch(round(lat, 1), round(lon, 1), int(bucket_hour.timestamp() // 1800))


def demo() -> None:
    assert _severity_from_conditions(20.0, 0.0) == 0.0
    assert _severity_from_conditions(20.0, 100.0) == 1.0
    assert _severity_from_conditions(-5.0, 0.0) == _TEMP_EXTREME_BUMP
    result = fetch(52.52, 13.41, datetime.now())  # noqa: DTZ005
    assert result.basis in ("computed", "unavailable")
    print(f"Berlin weather severity: {result.value} ({result.basis})")


if __name__ == "__main__":
    demo()
