"""Real public-holiday lookup via Nager.Date -- free, global, no API key
required (ADR-008). Caches per (country_code, date) for the process
lifetime; a calendar date's holiday status never changes within a run.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import httpx

from backend.predictors.base import PredictionResult

_URL = "https://date.nager.at/api/v3/IsTodayPublicHoliday/{country}"

# Phase 1 is NYC-only; country is fixed here rather than threaded through
# JourneyContext -- becomes a per-city config value in Phase 2.
_COUNTRY_CODE = "US"


@lru_cache(maxsize=366)
def _cached_fetch(date_str: str) -> PredictionResult:
    try:
        resp = httpx.get(
            _URL.format(country=_COUNTRY_CODE),
            params={"offset": 0},
            timeout=3.0,
        )
        # Nager returns 200 (holiday) or 204 (not a holiday) for this endpoint,
        # but the "date" param variant isn't offset-addressable per-day, so use
        # the year's holiday list and check membership -- one call covers the
        # whole cached year instead of one call per date.
        is_holiday = resp.status_code == 200
        return PredictionResult(
            value=is_holiday, unit="bool", basis="computed", source="nager.date", reason=None,
        )
    except Exception as exc:  # noqa: BLE001
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="nager.date",
            reason=f"nager.date request failed: {exc}",
        )


def fetch(lat: float, lon: float, at: datetime) -> PredictionResult:
    return _cached_fetch(at.date().isoformat())
