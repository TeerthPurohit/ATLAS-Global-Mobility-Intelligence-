"""Hybrid fare engine (ADR-007). Generalizes the additive fare formula
already in `stg_trips.sql` (`fare_amount + tolls + bcf + sales_tax +
congestion_surcharge + airport_fee + tip_amount`) -- but prospectively.

Honesty note, a deliberate deviation from a literal reading of the plan:
the trained fare model (`model_service.predict_fare`) predicts
`total_amount` directly -- it was never trained to decompose that number
into tolls/taxes/airport-fee sub-components, so this engine does NOT invent
per-component dollar figures for those (that would be exactly the
fabrication rule 2 forbids). What IS real: `base_fare` (the model's own
prediction, already reflecting historical toll/tax/airport-fee patterns
baked into its training label) plus three new, clearly-labeled prospective
adjustment terms this Phase 1 actually adds: vehicle class, historical
traffic, and weather. `vehicle_adjustment` is `computed` (a deterministic
multiplier from real seed data); `traffic_adjustment`/`weather_adjustment`/
`demand_adjustment` are `modeled_estimate` -- the dollar conversion of a
traffic/weather/demand *score* into a *surcharge* is this project's own
product rule, not a measured fact, same honesty bar as `congestion`'s
fusion in journey_predictors.py.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult, effective_confidence
from backend.predictors.journey_predictors import _demand_pressure
from backend.services import model_service, tariff_profiles

# Capped adjustment rates -- product configuration, not measured facts (see
# module docstring). Capped so a single adverse signal can't runaway the fare.
_TRAFFIC_MAX_PCT = 0.15
_WEATHER_MAX_PCT = 0.10
_DEMAND_MAX_PCT = 0.20

_MILES_TO_KM = 1.609344
# Applied only to cities whose tariff profile actually defines a
# peak_multiplier -- the window itself is product configuration, not a
# measured fact, same bar as the capped adjustment rates above.
_PEAK_HOURS = frozenset({7, 8, 9, 17, 18, 19})
# Same HIGH-bucket cutoff journey_predictors.predict_surge_risk uses on the
# same pressure signal -- surge_multiplier is this city's documented surge
# *ceiling* (see TariffCard's "Surge Ceiling" label), only real once actual
# demand momentum crosses into surge territory, never a permanent markup.
_SURGE_ACTIVE_THRESHOLD = 0.55

_CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "docs" / "tariff_calibration.json"


def _load_calibration() -> tuple[str, float | None]:
    """Real, measured MAPE from scripts/calibrate_tariff_nyc.py -- read once
    at import time, never a hardcoded guess (rule 2). Degrades honestly if
    the calibration script hasn't been run yet."""
    try:
        data = json.loads(_CALIBRATION_PATH.read_text())
        note = f"reproduces real NYC fares to within {data['mape_pct']}% MAPE when blind-tested (n={data['n']}, measured, N=1 city; see docs/tariff_calibration.json)"
        return note, float(data["mape_pct"])
    except Exception as exc:  # noqa: BLE001 -- calibration is a nice-to-have annotation, never a hard dependency
        logger.debug("pricing_engine._load_calibration step=missing path={} reason={}", _CALIBRATION_PATH, exc)
        return "calibration not yet measured -- run scripts/calibrate_tariff_nyc.py", None


_CALIBRATION_NOTE, CALIBRATION_MAPE_PCT = _load_calibration()


def _base_fare(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    """The real trained NYC fare model. `_base_fare_tariff` below is the
    other base-fare formula -- no longer reachable from a journey (there is
    only one city, and it has a trained model), but still the path
    `estimate_tariff_base_fare()` uses for the area-pair contract."""
    return _base_fare_nyc(ctx)


def _base_fare_nyc(ctx: JourneyContext) -> PredictionResult:
    if ctx.pickup_zone_id is None or ctx.dropoff_zone_id is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="xgboost_fare_v1",
            reason="pickup or dropoff location outside NYC zone coverage",
        )
    try:
        value, model_name = model_service.predict_fare(
            ctx.pickup_zone_id, ctx.dropoff_zone_id, ctx.departure_time.hour, ctx.departure_time.weekday(),
        )
    except KeyError as exc:
        logger.info("pricing_engine._base_fare_nyc step=no_fare_history reason={}", exc)
        return PredictionResult(value=None, unit=None, basis="unavailable", source="xgboost_fare_v1", reason=str(exc))
    except Exception as exc:  # noqa: BLE001 -- see below
        # A model artifact that won't score (e.g. an xgboost version whose
        # categorical container disagrees with the saved model) is a data
        # problem, not a request problem: degrade to an honest `unavailable`
        # like every other missing input, instead of 500ing the whole journey.
        logger.warning("pricing_engine._base_fare_nyc step=model_service.predict_fare failed: {}", exc)
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="xgboost_fare_v1",
            reason=f"fare model artifact could not be scored: {exc}",
        )
    return PredictionResult(
        value=round(value, 2), unit="USD", basis="computed", source=model_name, reason=None,
        data_vintage=model_service.data_vintage(),
        confidence=1.0, method="trained_fare_model",
    )


def _base_fare_tariff(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    profile = tariff_profiles.get()
    if profile is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="tariff_profile",
            reason="no tariff profile generated yet "
            "(see scripts/generate_tariff_profile.py)",
        )
    if features.distance_miles.value is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="tariff_profile", reason="distance unavailable",
        )
    km = features.distance_miles.value * _MILES_TO_KM
    minutes = features.duration_min.value if features.duration_min.value is not None else 0.0
    hour = ctx.departure_time.hour
    fare = profile.base_fare + profile.per_km * km + profile.per_min * minutes
    applied = ["base_fare", "per_km", "per_min"]

    # Flat components: added ONLY where this city's profile actually defines
    # one. A None here means "this city's tariff has no such fee" -- inventing
    # a default would be exactly the fabrication rule 2 forbids.
    for name in ("booking_fee", "platform_fee", "tolls"):
        amount = getattr(profile, name)
        if amount:
            fare += amount
            applied.append(name)

    # Time/context multipliers, same rule: only what the profile defines.
    if (hour >= 22 or hour < 5) and profile.night_multiplier:
        fare *= profile.night_multiplier
        applied.append("night_multiplier")
    if hour in _PEAK_HOURS and profile.peak_multiplier:
        fare *= profile.peak_multiplier
        applied.append("peak_multiplier")
    # City-level vehicle multiplier only; the per-vehicle-class factors live in
    # the vehicle_profiles seed and are applied once by _vehicle_adjustment().
    if profile.vehicle_multiplier:
        fare *= profile.vehicle_multiplier
        applied.append("vehicle_multiplier")
    if profile.surge_multiplier:
        sensitivity = features.vehicle_profile.demand_sensitivity if features.vehicle_profile else 1.0
        pressure = _demand_pressure(ctx)
        risk = min(1.0, pressure * sensitivity) if pressure is not None else 0.0
        if risk >= _SURGE_ACTIVE_THRESHOLD:
            fare *= profile.surge_multiplier
            applied.append("surge_multiplier")

    fare = max(fare, profile.min_fare)
    version = f" v{profile.version}" if profile.version else ""
    effective = f", effective from {profile.effective_from}" if profile.effective_from else ""
    return PredictionResult(
        value=round(fare, 2), unit=profile.currency, basis="modeled_estimate", source=f"tariff_profile:{profile.city_id}",
        reason=(
            f"{profile.source_type or profile.source} fare structure{version}{effective} "
            f"(confidence {profile.confidence:.0%}) anchored on NYC's real measured fares, no local trip data "
            f"exists for this city. Components applied: {', '.join(applied)} (min fare {profile.min_fare} "
            f"{profile.currency} floor). Method calibration: {_CALIBRATION_NOTE}. {profile.notes}"
        ),
        confidence=profile.confidence,
        method="tariff_profile_linear",
    )


def estimate_tariff_base_fare(distance_miles: float, hour: int) -> PredictionResult:
    """Base-fare-only tariff estimate for callers that have a distance and an
    hour but not a full JourneyContext (weather/holiday/vehicle adapters) --
    prediction_service.predict_fare()'s area_id-pair contract, unlike
    journey_service's full route estimate. Reuses _base_fare_tariff's linear
    formula so the two paths never drift into two different fare numbers for
    the same city; skips the adjustment terms that genuinely need route
    context (traffic/weather/demand), so this is deliberately a coarser
    number than /api/mobility/fare's -- reflected in `method` below so
    nothing conflates the two.
    """
    ctx = JourneyContext(
        pickup_lat=0.0, pickup_lon=0.0, dropoff_lat=0.0, dropoff_lon=0.0,
        departure_time=datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0),
        vehicle_type="car", pickup_zone_id=None, dropoff_zone_id=None, vehicle_profile=None,
        weather=PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="not resolved for this path"),
        holiday=PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="not resolved for this path"),
    )
    features = JourneyFeatures(
        distance_miles=PredictionResult(value=distance_miles, unit="miles", basis="computed", source="haversine"),
        duration_min=PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="not resolved for this path"),
        weather_score=ctx.weather, holiday_score=ctx.holiday,
        historical_traffic_score=PredictionResult(value=None, unit=None, basis="unavailable", source="n/a", reason="not resolved for this path"),
        vehicle_profile=None,
    )
    result = _base_fare_tariff(ctx, features)
    if result.value is None:
        return result
    return PredictionResult(
        value=result.value, unit=result.unit, basis=result.basis, source=result.source,
        reason=f"{result.reason} (base fare only -- no route/weather/demand context available on this endpoint)",
        confidence=result.confidence, method="tariff_profile_linear_base_only",
    )


def _vehicle_adjustment(base_fare: PredictionResult, features: JourneyFeatures) -> PredictionResult:
    if base_fare.value is None or features.vehicle_profile is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="vehicle_profiles_seed",
            reason="base fare unavailable or unrecognized vehicle_class",
        )
    delta = round(base_fare.value * (features.vehicle_profile.base_fare_factor - 1.0), 2)
    return PredictionResult(value=delta, unit=base_fare.unit, basis="computed", source="vehicle_profiles_seed", reason=None)


def _traffic_adjustment(base_fare: PredictionResult, features: JourneyFeatures) -> PredictionResult:
    traffic = features.historical_traffic_score
    if base_fare.value is None or traffic.basis == "unavailable" or traffic.value is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="traffic_adjustment",
            reason="base fare or historical traffic score unavailable",
        )
    sensitivity = features.vehicle_profile.traffic_sensitivity if features.vehicle_profile else 1.0
    delta = round(base_fare.value * _TRAFFIC_MAX_PCT * traffic.value * sensitivity, 2)
    return PredictionResult(
        value=delta, unit=base_fare.unit, basis="modeled_estimate", source="traffic_adjustment",
        reason=f"up to {_TRAFFIC_MAX_PCT:.0%} surcharge scaled by historical traffic score, a product rule not a measured fact",
    )


def _weather_adjustment(base_fare: PredictionResult, features: JourneyFeatures) -> PredictionResult:
    weather = features.weather_score
    if base_fare.value is None or weather.basis == "unavailable" or weather.value is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="weather_adjustment",
            reason="base fare unavailable, or weather adapter unavailable (see reason on weather_score)",
        )
    delta = round(base_fare.value * _WEATHER_MAX_PCT * weather.value, 2)
    return PredictionResult(
        value=delta, unit=base_fare.unit, basis="modeled_estimate", source="weather_adjustment",
        reason=f"up to {_WEATHER_MAX_PCT:.0%} surcharge scaled by live weather severity, a product rule not a measured fact",
    )


def _demand_adjustment(ctx: JourneyContext, base_fare: PredictionResult, features: JourneyFeatures) -> PredictionResult:
    if base_fare.value is None or ctx.pickup_zone_id is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="demand_adjustment",
            reason="base fare unavailable or pickup location outside the zone coverage",
        )
    # Same real zone-momentum signal journey_predictors.predict_availability/
    # predict_surge_risk already use -- reused rather than re-deriving a
    # second pressure formula here.
    pressure = _demand_pressure(ctx)
    if pressure is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="demand_adjustment",
            reason="no demand history for this zone",
        )
    sensitivity = features.vehicle_profile.demand_sensitivity if features.vehicle_profile else 1.0
    delta = round(base_fare.value * _DEMAND_MAX_PCT * pressure * sensitivity, 2)
    return PredictionResult(
        value=delta, unit=base_fare.unit, basis="modeled_estimate", source="demand_adjustment",
        reason=f"up to {_DEMAND_MAX_PCT:.0%} surcharge scaled by current demand momentum, a product rule not a measured fact",
    )


def compute_fare(ctx: JourneyContext, features: JourneyFeatures) -> dict[str, PredictionResult]:
    logger.debug("pricing_engine.compute_fare step=start")
    base_fare = _base_fare(ctx, features)
    logger.debug("pricing_engine.compute_fare step=base_fare basis={} value={}", base_fare.basis, base_fare.value)
    terms = {
        "base_fare": base_fare,
        "vehicle_adjustment": _vehicle_adjustment(base_fare, features),
        "traffic_adjustment": _traffic_adjustment(base_fare, features),
        "weather_adjustment": _weather_adjustment(base_fare, features),
        "demand_adjustment": _demand_adjustment(ctx, base_fare, features),
    }
    if base_fare.value is None:
        terms["total"] = PredictionResult(
            value=None, unit=None, basis="unavailable", source="pricing_engine",
            reason="base fare unavailable",
        )
        return terms

    included = [t for t in terms.values() if t.value is not None]
    total_value = round(sum(t.value for t in included), 2)
    total_basis = "computed" if all(t.basis == "computed" for t in included) else "modeled_estimate"
    excluded = [name for name, t in terms.items() if t.value is None]
    reason = None if total_basis == "computed" else (
        "includes modeled_estimate adjustment term(s)" + (f"; excluded: {', '.join(excluded)}" if excluded else "")
    )
    # Weakest-link, not an average: a sum is only as trustworthy as its least
    # trustworthy term, and averaging would let three cheap adjustments dilute
    # a genuinely uncertain base fare upward.
    terms["total"] = PredictionResult(
        value=total_value, unit=base_fare.unit, basis=total_basis, source="pricing_engine", reason=reason,
        confidence=min(effective_confidence(t) for t in included),
        method=f"{base_fare.method or 'base_fare'}+adjustments",
    )
    return terms
