"""Real public-holiday lookup via Nager.Date -- free, global, no API key
required (ADR-008). Caches per (year, country_code) for the process
lifetime; a year's holiday calendar never changes within a run.

Uses the `PublicHolidays/{year}/{country}` endpoint (returns every holiday
date in that year), then checks membership for the requested date --
Nager's `IsTodayPublicHoliday` endpoint (used by an earlier version of this
file) always checks the server's *real current date* regardless of any date
passed to it, silently returning wrong answers for any historical/future
`at` argument. The year-list approach is also cheaper: one call covers an
entire year instead of one call per date.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import httpx

from backend.predictors.base import PredictionResult

_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"

# Default when no country_code is supplied -- keeps the one existing NYC
# journey-pipeline call site (journey_service.py, 3 positional args) working
# unchanged. Any other city passes its own real country_code explicitly.
_DEFAULT_COUNTRY_CODE = "US"


@lru_cache(maxsize=200)
def _year_holidays(year: int, country_code: str) -> frozenset[str] | None:
    """Real holiday dates (ISO strings) for a (year, country), or None if the
    lookup itself failed (distinct from "fetched successfully, zero holidays
    this year" -- which frozenset() also represents correctly)."""
    try:
        resp = httpx.get(_URL.format(year=year, country=country_code), timeout=4.0)
        resp.raise_for_status()
        rows = resp.json()
        return frozenset(r["date"] for r in rows)
    except Exception:  # noqa: BLE001 -- caller turns this into an honest PredictionResult
        return None


def fetch(lat: float, lon: float, at: datetime, country_code: str | None = None) -> PredictionResult:
    country = (country_code or _DEFAULT_COUNTRY_CODE).upper()
    date_str = at.date().isoformat()
    holidays = _year_holidays(at.year, country)
    if holidays is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="nager.date",
            reason=f"nager.date request failed for country_code={country!r} year={at.year}",
        )
    return PredictionResult(
        value=date_str in holidays, unit="bool", basis="computed", source="nager.date", reason=None,
    )


def demo() -> None:
    # A real, well-known fixed-date US holiday -- Independence Day always
    # falls on July 4th regardless of year.
    result = fetch(40.7128, -74.0060, datetime(2024, 7, 4), country_code="US")
    assert result.basis in ("computed", "unavailable")
    if result.basis == "computed":
        assert result.value is True, "2024-07-04 should resolve as a US holiday (Independence Day)"
    non_holiday = fetch(40.7128, -74.0060, datetime(2024, 3, 15), country_code="US")
    if non_holiday.basis == "computed":
        assert non_holiday.value is False
    print(f"July 4 2024 US holiday: {result.value} ({result.basis})")


if __name__ == "__main__":
    demo()
