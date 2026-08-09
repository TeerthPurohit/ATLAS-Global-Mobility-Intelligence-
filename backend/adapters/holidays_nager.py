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

For the ~37 countries Nager.Date doesn't cover at all (notably India),
falls back to `dbt_project/seeds/fixed_holidays_extended.csv`
(scripts/extract_fixed_holidays.py) -- a real global 2010-2019 calendar,
reduced to only the (country, month, day) combinations that were a holiday
in literally every one of those 10 years, i.e. fixed-date holidays a
floating holiday (Eid, Diwali, ...) could never satisfy by coincidence.
Never used to override a country Nager.Date already answers live.
"""
from __future__ import annotations

import csv
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import httpx

from backend.predictors.base import PredictionResult

_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"
_EXTENDED_SEED_PATH = Path(__file__).resolve().parents[2] / "dbt_project" / "seeds" / "fixed_holidays_extended.csv"

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


@lru_cache(maxsize=1)
def _extended_fixed_holidays() -> frozenset[tuple[str, int, int]]:
    if not _EXTENDED_SEED_PATH.exists():
        return frozenset()
    with open(_EXTENDED_SEED_PATH, newline="", encoding="utf-8") as f:
        return frozenset((row["country_code"], int(row["month"]), int(row["day"])) for row in csv.DictReader(f))


def fetch(lat: float, lon: float, at: datetime, country_code: str | None = None) -> PredictionResult:
    country = (country_code or _DEFAULT_COUNTRY_CODE).upper()
    date_str = at.date().isoformat()
    holidays = _year_holidays(at.year, country)
    if holidays is not None:
        return PredictionResult(
            value=date_str in holidays, unit="bool", basis="computed", source="nager.date", reason=None,
        )

    if (country, at.month, at.day) in _extended_fixed_holidays():
        return PredictionResult(
            value=True, unit="bool", basis="modeled_estimate", source="fixed_holidays_extended",
            reason=f"nager.date does not cover country_code={country!r}; this (month, day) was a public "
            "holiday in every year of a real 2010-2019 calendar, extrapolated forward as a fixed-date "
            "holiday (never used for floating holidays, which wouldn't satisfy that rule)",
        )
    if country in {c for c, _, _ in _extended_fixed_holidays()}:
        # We do have extended coverage for this country -- a real "not a
        # fixed holiday on this date" answer, not a blanket "no data".
        return PredictionResult(
            value=False, unit="bool", basis="modeled_estimate", source="fixed_holidays_extended",
            reason=f"nager.date does not cover country_code={country!r}; not one of its known fixed-date holidays "
            "(floating holidays like Eid/Diwali aren't covered by this fallback)",
        )
    return PredictionResult(
        value=None, unit=None, basis="unavailable", source="nager.date",
        reason=f"nager.date request failed for country_code={country!r} year={at.year}, "
        "and no extended fixed-holiday coverage exists for this country either",
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

    # India isn't in Nager.Date's 204 countries -- exercises the extended
    # fixed-date fallback (scripts/extract_fixed_holidays.py).
    india_independence_day = fetch(19.076, 72.8777, datetime(2026, 8, 15), country_code="IN")
    assert india_independence_day.basis == "modeled_estimate"
    assert india_independence_day.value is True
    india_ordinary_day = fetch(19.076, 72.8777, datetime(2026, 8, 9), country_code="IN")
    assert india_ordinary_day.value is False
    print(f"India Aug 15 holiday (extended fallback): {india_independence_day.value} ({india_independence_day.basis})")


if __name__ == "__main__":
    demo()
