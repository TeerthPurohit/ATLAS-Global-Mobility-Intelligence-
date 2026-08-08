"""Cross-city demand-per-capita estimation (SPEC-015 FR-5).

Scoped to `models/` only: the spec's literal path
(`backend/services/estimation_service.py`) is deliberately NOT created here
-- a separate backend-engineer track is concurrently touching
`backend/services/` and the thin `basis="modeled_estimate"` wrapper that
calls this module gets built there later, the same way
`backend/services/model_service.py` merely loads/wraps the artifacts
`models/xgboost_model/` produces. This module's job stops at being the
honest, real-data-grounded core that wrapper will call.

Real reference points (rule 2 -- every number below traces to a real query
or a named, dated public source; nothing invented):

NYC (ride-hailing pickups, `zone_hourly_demand` mart):
    total_trips = 7,998,849 over 92 real dates the warehouse actually has
    (Jan+Mar+Jun 2024 -- Feb/Apr/May are a known warehouse gap, see
    `.claude/memory.md`'s "Data gap: only Jan/Mar/Jun" note), 261 zones.
    `SELECT SUM(total_trips), COUNT(DISTINCT pickup_date) FROM
    zone_hourly_demand` against data/warehouse/nyc_rides.duckdb, run
    2026-08-08.
    population = 8,804,190 -- U.S. Census Bureau, 2020 Decennial Census,
    "New York city, New York" total population.
    https://www.census.gov/quickfacts/newyorkcitynewyork
    land area = 778.2 km^2 (300.46 sq mi) -- same Census-sourced figure,
    via https://en.wikipedia.org/wiki/New_York_City.

London (Santander Cycle Hire bike-share departures,
    `london_station_hourly_demand` mart -- NOT ride-hailing, see the
    honesty caveat below):
    total_trips = 2,192,353 over 95 real dates the warehouse actually has
    (2026-01-01 to 2026-06-01, itself a 3-block-with-gaps range, not
    continuous -- verified against the real data; see
    `tests/test_london_pipeline.py`), 804 stations.
    `SELECT SUM(total_trips), COUNT(DISTINCT trip_date) FROM
    london_station_hourly_demand` against data/warehouse/london_cycles.duckdb,
    run 2026-08-08.
    population = 9,089,736 -- Office for National Statistics (ONS) mid-2024
    population estimate for Greater London.
    https://en.wikipedia.org/wiki/Greater_London
    land area = 1,572 km^2 -- same ONS-sourced figure, same page.

**Honesty caveat (do not remove, per SPEC-015 Risk 1 and rule 2):** these
are two different mobility products, not a like-for-like comparison. NYC's
number is aggregate ride-hailing pickups (any trip, any purpose). London's
is Santander Cycle Hire bike-share departures -- a narrow, discretionary
transport mode used by a small fraction of Londoners, not general urban
mobility demand. Computing a ratio between them and calling it a "scaling
factor" is already a stretch with N=2 real data points; every value this
module returns says so plainly in its `reason` string rather than hiding it
behind a precise-looking number.
"""

from __future__ import annotations

# ---- NYC reference point -----------------------------------------------
NYC_TOTAL_TRIPS = 7_998_849
NYC_N_DAYS = 92
NYC_POPULATION = 8_804_190
NYC_LAND_AREA_KM2 = 778.2
NYC_POPULATION_SOURCE = (
    "U.S. Census Bureau, 2020 Decennial Census, \"New York city, New York\" "
    "total population -- https://www.census.gov/quickfacts/newyorkcitynewyork"
)

# ---- London reference point ---------------------------------------------
LONDON_TOTAL_TRIPS = 2_192_353
LONDON_N_DAYS = 95
LONDON_POPULATION = 9_089_736
LONDON_LAND_AREA_KM2 = 1572.0
LONDON_POPULATION_SOURCE = (
    "Office for National Statistics (ONS), mid-2024 population estimate for "
    "Greater London -- https://en.wikipedia.org/wiki/Greater_London"
)


def _daily_trips_per_capita(total_trips: int, n_days: int, population: int) -> float:
    return (total_trips / n_days) / population


NYC_DAILY_RATE_PER_CAPITA = _daily_trips_per_capita(NYC_TOTAL_TRIPS, NYC_N_DAYS, NYC_POPULATION)
LONDON_DAILY_RATE_PER_CAPITA = _daily_trips_per_capita(LONDON_TOTAL_TRIPS, LONDON_N_DAYS, LONDON_POPULATION)
NYC_DENSITY_PER_KM2 = NYC_POPULATION / NYC_LAND_AREA_KM2
LONDON_DENSITY_PER_KM2 = LONDON_POPULATION / LONDON_LAND_AREA_KM2
_AVG_REFERENCE_DENSITY = (NYC_DENSITY_PER_KM2 + LONDON_DENSITY_PER_KM2) / 2

# Density is a stretch-goal covariate (SPEC-015 Data Design): with only two
# reference points there's no real basis for a precise density-elasticity
# fit, so the density adjustment is a mild, clamped multiplier -- denser than
# the two references' average nudges the estimate up, sparser nudges it
# down, never more than 2x either way. This is a documented simplification,
# not a fitted regression.
_DENSITY_MULTIPLIER_MIN = 0.5
_DENSITY_MULTIPLIER_MAX = 2.0


def estimate_demand_per_capita(population: int, density: float | None = None) -> tuple[float, str]:
    """Rough order-of-magnitude estimate of daily mobility-demand volume for
    a city of the given population, scaled from the NYC/London demand-per-
    capita reference points (mirrors `model_service.predict_demand()`'s
    `(value, reason)` return convention).

    `density` is people/km^2, optional. N=2 calibration points -- see module
    docstring's honesty caveat. Never presented as a validated model; the
    returned `reason` always states the real low/high range implied by the
    two reference rates, not just a single point estimate.
    """
    if population <= 0:
        raise ValueError(f"population must be positive, got {population}")

    low_rate = min(NYC_DAILY_RATE_PER_CAPITA, LONDON_DAILY_RATE_PER_CAPITA)
    high_rate = max(NYC_DAILY_RATE_PER_CAPITA, LONDON_DAILY_RATE_PER_CAPITA)
    mid_rate = (low_rate + high_rate) / 2

    density_note = ""
    if density is not None and density > 0:
        multiplier = max(_DENSITY_MULTIPLIER_MIN, min(_DENSITY_MULTIPLIER_MAX, density / _AVG_REFERENCE_DENSITY))
        mid_rate *= multiplier
        density_note = (
            f" density-adjusted by a clamped {multiplier:.2f}x multiplier "
            f"(target {density:.0f}/km^2 vs. the two references' average "
            f"{_AVG_REFERENCE_DENSITY:.0f}/km^2 -- not a fitted elasticity, "
            "just a bounded nudge)."
        )

    value = round(population * mid_rate, 1)
    low = round(population * low_rate, 1)
    high = round(population * high_rate, 1)

    reason = (
        "very rough, N=2 calibration (NYC ride-hailing pickups vs. London "
        "Santander Cycle Hire bike-share departures -- not the same mobility "
        f"product, see module docstring): implied daily-demand range for a "
        f"population of {population:,} is roughly {low:,.0f}-{high:,.0f} "
        f"trips/day (midpoint used as the point value below)."
        f"{density_note} Treat this as an order-of-magnitude guide only, "
        "never a validated model."
    )
    return value, reason


def demo() -> None:
    """Smallest runnable self-check: the two real reference rates land on
    opposite sides of a plausible per-capita band, and a third population
    gets an honestly-labeled (never 'computed') estimate."""
    assert 0 < LONDON_DAILY_RATE_PER_CAPITA < NYC_DAILY_RATE_PER_CAPITA, (
        "London bike-share per-capita rate should be well below NYC's "
        "all-purpose ride-hailing rate"
    )
    value, reason = estimate_demand_per_capita(1_000_000)
    assert value > 0
    assert "N=2" in reason and "never a validated model" in reason
    value_dense, reason_dense = estimate_demand_per_capita(1_000_000, density=15000)
    assert value_dense != value
    assert "density-adjusted" in reason_dense
    print(f"NYC daily rate/capita:    {NYC_DAILY_RATE_PER_CAPITA:.6f}")
    print(f"London daily rate/capita: {LONDON_DAILY_RATE_PER_CAPITA:.6f}")
    print(f"1M population estimate:  {value:,.0f} trips/day -- {reason}")
    print("estimate.py demo OK")


if __name__ == "__main__":
    demo()
