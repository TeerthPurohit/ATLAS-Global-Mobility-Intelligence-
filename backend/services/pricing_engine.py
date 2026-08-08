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

from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult
from backend.services import model_service

# Capped adjustment rates -- product configuration, not measured facts (see
# module docstring). Capped so a single adverse signal can't runaway the fare.
_TRAFFIC_MAX_PCT = 0.15
_WEATHER_MAX_PCT = 0.10
_DEMAND_MAX_PCT = 0.20


def _base_fare(ctx: JourneyContext) -> PredictionResult:
    if ctx.pickup_zone_id is None or ctx.dropoff_zone_id is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="xgboost_fare_v1",
            reason="pickup or dropoff location outside NYC zone coverage",
        )
    try:
        value, model_name = model_service.predict_fare(ctx.pickup_zone_id, ctx.dropoff_zone_id, ctx.departure_time.hour)
    except KeyError as exc:
        return PredictionResult(value=None, unit=None, basis="unavailable", source="xgboost_fare_v1", reason=str(exc))
    return PredictionResult(value=round(value, 2), unit="usd", basis="computed", source=model_name, reason=None)


def _vehicle_adjustment(base_fare: PredictionResult, features: JourneyFeatures) -> PredictionResult:
    if base_fare.value is None or features.vehicle_profile is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="vehicle_profiles_seed",
            reason="base fare unavailable or unrecognized vehicle_class",
        )
    delta = round(base_fare.value * (features.vehicle_profile.base_fare_factor - 1.0), 2)
    return PredictionResult(value=delta, unit="usd", basis="computed", source="vehicle_profiles_seed", reason=None)


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
        value=delta, unit="usd", basis="modeled_estimate", source="traffic_adjustment",
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
        value=delta, unit="usd", basis="modeled_estimate", source="weather_adjustment",
        reason=f"up to {_WEATHER_MAX_PCT:.0%} surcharge scaled by live weather severity, a product rule not a measured fact",
    )


def _demand_adjustment(ctx: JourneyContext, base_fare: PredictionResult, features: JourneyFeatures) -> PredictionResult:
    if base_fare.value is None or ctx.pickup_zone_id is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="demand_adjustment",
            reason="base fare unavailable or pickup location outside NYC zone coverage",
        )
    momentum = model_service.get_zone_momentum(ctx.pickup_zone_id)
    if momentum is None or momentum["rolling_7d_avg"] <= 0:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="demand_adjustment",
            reason="no demand history for this zone",
        )
    pressure = max(0.0, min(1.0, momentum["lag_1h"] / momentum["rolling_7d_avg"] / 2.0))
    sensitivity = features.vehicle_profile.demand_sensitivity if features.vehicle_profile else 1.0
    delta = round(base_fare.value * _DEMAND_MAX_PCT * pressure * sensitivity, 2)
    return PredictionResult(
        value=delta, unit="usd", basis="modeled_estimate", source="demand_adjustment",
        reason=f"up to {_DEMAND_MAX_PCT:.0%} surcharge scaled by current demand momentum, a product rule not a measured fact",
    )


def compute_fare(ctx: JourneyContext, features: JourneyFeatures) -> dict[str, PredictionResult]:
    base_fare = _base_fare(ctx)
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
    terms["total"] = PredictionResult(value=total_value, unit="usd", basis=total_basis, source="pricing_engine", reason=reason)
    return terms
