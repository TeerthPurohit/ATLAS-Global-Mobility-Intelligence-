"""Estimation service (SPEC-015 FR-5) -- thin backend wrapper around
`models/cross_city_estimation/estimate.py`.

Provides tier-2 demand estimation for cities with population covariates but no
real trip-level model, returning structured `PredictionResult` objects with
`basis="modeled_estimate"` and an honest, explicit reason string explaining
the 2-reference-point scaling basis.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from datetime import datetime  # noqa: E402

from backend.adapters import cost_of_living_worldbank, holidays_nager, weather_openmeteo  # noqa: E402
from backend.predictors.base import PredictionResult  # noqa: E402
from models.cross_city_estimation.estimate import (  # noqa: E402
    NYC_FARE_PER_MILE,
    NYC_FARE_PER_MILE_SOURCE,
    estimate_demand_per_capita,
)

logger = logging.getLogger(__name__)

# A wet-hour "is it raining" signal derived from the request-time weather
# severity score is a coarser proxy than the real precipitation_mm the
# elasticity was measured against, but it's the only real-time signal
# available without a second live weather call -- any nonzero severity from
# precipitation implies some rain is falling.
_WET_SEVERITY_THRESHOLD = 0.05


def estimate_city_demand(
    city_id: str, population: int, density: float | None = None,
    lat: float | None = None, lon: float | None = None, at: datetime | None = None,
) -> PredictionResult:
    """Estimate daily demand volume for a city using NYC/London demand-per-capita
    scaling, optionally adjusted by real weather/holiday signals for (lat, lon, at).

    Always returns `basis="modeled_estimate"` with a clear non-validated reason,
    never `computed` (rule 2 / ADR-007 discipline). Falls back to the unadjusted
    estimate if lat/lon/at aren't supplied, or if either adapter is unavailable
    -- weather/holiday context is a bonus signal, never a blocker.
    """
    if population <= 0:
        return PredictionResult(
            value=None,
            unit="trips/day",
            basis="unavailable",
            source="cross_city_estimation",
            reason=f"population covariate must be positive, got {population}",
        )

    is_wet = None
    is_holiday = None
    if lat is not None and lon is not None and at is not None:
        weather_res = weather_openmeteo.fetch(lat, lon, at)
        if weather_res.basis == "computed" and weather_res.value is not None:
            is_wet = weather_res.value >= _WET_SEVERITY_THRESHOLD
        holiday_res = holidays_nager.fetch(lat, lon, at)
        if holiday_res.basis == "computed":
            is_holiday = bool(holiday_res.value)

    val, reason = estimate_demand_per_capita(population, density, is_wet=is_wet, is_holiday=is_holiday)
    logger.info("estimation_service: city_id=%s population=%d -> estimate=%.1f", city_id, population, val)
    return PredictionResult(
        value=val,
        unit="trips/day",
        basis="modeled_estimate",
        source="cross_city_estimation (NYC/London 2-point reference scaling)",
        reason=reason,
    )


def estimate_fare_per_mile(country_code: str | None) -> PredictionResult:
    """NYC's real fare-per-mile rate, scaled by the ratio of the target
    country's World Bank PPP conversion factor to the US's -- a purchasing-
    power proxy, never a real local fare survey. Always `modeled_estimate`
    on success, honest `unavailable` if either PPP lookup fails (the World
    Bank API has real-world reliability gaps -- see cost_of_living_worldbank.py).
    """
    if not country_code:
        return PredictionResult(
            value=None, unit="usd_per_mile", basis="unavailable", source="cost_of_living_worldbank",
            reason="no country_code resolvable for this location",
        )
    us_ppp = cost_of_living_worldbank.fetch("US")
    target_ppp = cost_of_living_worldbank.fetch(country_code)
    if us_ppp.basis == "unavailable" or target_ppp.basis == "unavailable" or not us_ppp.value:
        return PredictionResult(
            value=None, unit="usd_per_mile", basis="unavailable", source="cost_of_living_worldbank",
            reason=(target_ppp.reason if target_ppp.basis == "unavailable" else us_ppp.reason)
            or "PPP conversion factor lookup failed",
        )
    ratio = target_ppp.value / us_ppp.value
    value = round(NYC_FARE_PER_MILE * ratio, 2)
    reason = (
        f"NYC's real fare-per-mile rate (${NYC_FARE_PER_MILE:.2f}/mile -- {NYC_FARE_PER_MILE_SOURCE}) "
        f"scaled by the ratio of {country_code.upper()!r}'s World Bank PPP conversion factor to the "
        f"US's ({ratio:.2f}x) -- a purchasing-power proxy, not a real local fare survey. "
        "Treat as order-of-magnitude only."
    )
    return PredictionResult(
        value=value, unit="usd_per_mile", basis="modeled_estimate",
        source="cost_of_living_worldbank + cross_city_estimation", reason=reason,
    )
