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
from pathlib import Path

from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult
from backend.services import model_service, tariff_profiles

# Capped adjustment rates -- product configuration, not measured facts (see
# module docstring). Capped so a single adverse signal can't runaway the fare.
_TRAFFIC_MAX_PCT = 0.15
_WEATHER_MAX_PCT = 0.10
_DEMAND_MAX_PCT = 0.20

_MILES_TO_KM = 1.609344

_CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "docs" / "tariff_calibration.json"


def _load_calibration() -> tuple[str, float | None]:
    """Real, measured MAPE from scripts/calibrate_tariff_nyc.py -- read once
    at import time, never a hardcoded guess (rule 2). Degrades honestly if
    the calibration script hasn't been run yet."""
    try:
        data = json.loads(_CALIBRATION_PATH.read_text())
        note = f"reproduces real NYC fares to within {data['mape_pct']}% MAPE when blind-tested (n={data['n']}, measured, N=1 city; see docs/tariff_calibration.json)"
        return note, float(data["mape_pct"])
    except Exception:  # noqa: BLE001 -- calibration is a nice-to-have annotation, never a hard dependency
        return "calibration not yet measured -- run scripts/calibrate_tariff_nyc.py", None


_CALIBRATION_NOTE, CALIBRATION_MAPE_PCT = _load_calibration()


def _base_fare(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    """NYC (a real trained model) or a `TariffProfile` (ADR-011) everywhere
    else -- one dispatch point, same downstream adjustment terms regardless
    of which base fare produced the number they're a percentage of."""
    if ctx.city_id == "nyc":
        return _base_fare_nyc(ctx)
    return _base_fare_tariff(ctx, features)


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
        return PredictionResult(value=None, unit=None, basis="unavailable", source="xgboost_fare_v1", reason=str(exc))
    return PredictionResult(
        value=round(value, 2), unit="USD", basis="computed", source=model_name, reason=None,
        data_vintage=model_service.data_vintage("nyc"),
    )


def _base_fare_tariff(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    profile = tariff_profiles.get(ctx.city_id)
    if profile is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="tariff_profile",
            reason=f"no tariff profile generated yet for city_id={ctx.city_id!r} "
            "(see scripts/generate_tariff_profile.py)",
        )
    if features.distance_miles.value is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="tariff_profile", reason="distance unavailable",
        )
    km = features.distance_miles.value * _MILES_TO_KM
    minutes = features.duration_min.value if features.duration_min.value is not None else 0.0
    is_night = ctx.departure_time.hour >= 22 or ctx.departure_time.hour < 5
    fare = profile.base_fare + profile.per_km * km + profile.per_min * minutes
    if is_night:
        fare *= profile.night_multiplier
    fare = max(fare, profile.min_fare)
    return PredictionResult(
        value=round(fare, 2), unit=profile.currency, basis="modeled_estimate", source=f"tariff_profile:{ctx.city_id}",
        reason=(
            f"LLM-derived fare structure (confidence {profile.confidence:.0%}) anchored on NYC's real measured "
            f"fares, no local trip data exists for this city. Method calibration: {_CALIBRATION_NOTE}. {profile.notes}"
        ),
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
            reason=f"base fare unavailable or pickup location outside {ctx.city_id}'s zone coverage",
        )
    momentum = model_service.get_zone_momentum(ctx.pickup_zone_id, ctx.city_id)
    if momentum is None or momentum["rolling_7d_avg"] <= 0:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="demand_adjustment",
            reason="no demand history for this zone",
        )
    pressure = max(0.0, min(1.0, momentum["lag_1h"] / momentum["rolling_7d_avg"] / 2.0))
    sensitivity = features.vehicle_profile.demand_sensitivity if features.vehicle_profile else 1.0
    delta = round(base_fare.value * _DEMAND_MAX_PCT * pressure * sensitivity, 2)
    return PredictionResult(
        value=delta, unit=base_fare.unit, basis="modeled_estimate", source="demand_adjustment",
        reason=f"up to {_DEMAND_MAX_PCT:.0%} surcharge scaled by current demand momentum, a product rule not a measured fact",
    )


def compute_fare(ctx: JourneyContext, features: JourneyFeatures) -> dict[str, PredictionResult]:
    base_fare = _base_fare(ctx, features)
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
    terms["total"] = PredictionResult(value=total_value, unit=base_fare.unit, basis=total_basis, source="pricing_engine", reason=reason)
    return terms
