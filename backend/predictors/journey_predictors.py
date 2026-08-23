"""Journey predictors (ADR-007). Each function takes the shared
`JourneyContext`/`JourneyFeatures` (never a raw adapter dict) and returns one
`PredictionResult`. Distance/ETA aren't separate predictors here -- they're
resolved once in `journey_service.build_features()` and reported straight
from `JourneyFeatures`, since every other predictor needs them as an input
too (fixed predictor order, ADR-007 §6).
"""
from __future__ import annotations

from backend.predictors.base import (
    BASIS_CONFIDENCE,
    JourneyContext,
    JourneyFeatures,
    PredictionResult,
    effective_confidence,
)
from backend.services import model_service

_ZONE_MODEL_CITIES = ("nyc",)


def predict_demand(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    if ctx.pickup_zone_id is not None and ctx.city_id in _ZONE_MODEL_CITIES:
        try:
            value, model_name = model_service.predict_demand(
                ctx.pickup_zone_id, ctx.departure_time.hour, ctx.departure_time.weekday(),
                city_id=ctx.city_id, month=ctx.departure_time.month,
            )
        except KeyError as exc:
            return PredictionResult(value=None, unit=None, basis="unavailable", source="demand", reason=str(exc))
        return PredictionResult(
            value=round(value, 2), unit="trips_per_hour", basis="computed", source=model_name, reason=None,
            data_vintage=model_service.data_vintage(ctx.city_id),
            confidence=1.0, method="zone_demand_model",
        )
    return PredictionResult(
        value=None, unit=None, basis="unavailable", source="demand",
        reason=f"pickup location outside {ctx.city_id}'s zone coverage",
    )


def predict_fare_range(base_fare: PredictionResult, test_rmse: float | None = None, fraction: float | None = None) -> PredictionResult:
    # base_fare here is the fare TOTAL (may legitimately be "modeled_estimate"
    # if any pricing adjustment term was a modeled_estimate, per
    # pricing_engine.compute_fare) -- only a missing value makes the range
    # unavailable, not a non-"computed" basis. The range honestly inherits
    # whichever basis the total actually has.
    #
    # NYC passes a fixed `test_rmse` (a real dollar figure measured on the
    # trained fare model's test split). Every other city passes `fraction`
    # instead -- an absolute USD RMSE has no meaning against a tariff fare
    # denominated in INR/JPY/NGN; a percentage band (the measured LLM-tariff
    # calibration MAPE, see pricing_engine.CALIBRATION_MAPE_PCT) scales with
    # whatever currency the fare is actually in.
    if base_fare.value is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="fare_range",
            reason="base fare unavailable, range cannot be computed",
        )
    if test_rmse is not None:
        low, high = max(0.0, base_fare.value - test_rmse), base_fare.value + test_rmse
        source = "xgboost_fare_v1_measured_rmse"
    else:
        frac = (fraction if fraction is not None else 20.0) / 100.0
        low, high = max(0.0, base_fare.value * (1 - frac)), base_fare.value * (1 + frac)
        source = "tariff_profile_measured_mape"
    reason = None if base_fare.basis == "computed" else "range applied on top of a modeled_estimate fare total"
    return PredictionResult(
        value=f"{low:.2f}-{high:.2f}", unit=base_fare.unit, basis=base_fare.basis, source=source,
        reason=reason,
        confidence=effective_confidence(base_fare), method=source,
    )


def predict_carbon(features: JourneyFeatures) -> PredictionResult:
    if features.distance_miles.basis == "unavailable" or features.distance_miles.value is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="carbon",
            reason="distance unavailable, carbon cannot be computed",
        )
    if features.vehicle_profile is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="carbon",
            reason="unrecognized vehicle_class",
        )
    kg = round(features.distance_miles.value * features.vehicle_profile.emission_factor, 2)
    # Deterministic arithmetic over a real distance and a seeded emission
    # factor -- confidence inherits the distance's, since that's the only
    # uncertain input.
    return PredictionResult(
        value=kg, unit="kg_co2", basis="computed", source="vehicle_profiles_seed", reason=None,
        confidence=effective_confidence(features.distance_miles), method="emission_factor_x_distance",
    )


def predict_congestion(features: JourneyFeatures) -> PredictionResult:
    traffic = features.historical_traffic_score
    weather = features.weather_score
    if traffic.basis == "unavailable" and weather.basis == "unavailable":
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="congestion",
            reason="no historical traffic or weather signal available",
        )
    traffic_component = traffic.value if traffic.basis != "unavailable" and traffic.value is not None else 0.0
    weather_component = weather.value if weather.basis != "unavailable" and weather.value is not None else 0.0
    score = min(1.0, 0.7 * traffic_component + 0.3 * weather_component)
    bucket = "LOW" if score < 0.25 else "MODERATE" if score < 0.5 else "HIGH" if score < 0.75 else "SEVERE"
    # The fusion has no ground truth, so its confidence is capped at the
    # modeled_estimate default and scaled by how many of its two inputs were
    # actually available -- one-legged fusion is genuinely less trustworthy.
    inputs_present = sum(p.basis != "unavailable" for p in (traffic, weather))
    return PredictionResult(
        value=bucket, unit=None, basis="modeled_estimate", source="congestion_fusion",
        reason=f"fusion of historical speed and weather severity (score={score:.2f}), no ground truth for the fusion itself",
        confidence=round(BASIS_CONFIDENCE["modeled_estimate"] * inputs_present / 2, 2),
        method="traffic_weather_fusion",
        score=round(score, 2),
    )


def _demand_pressure(ctx: JourneyContext) -> float | None:
    """Real momentum-based signal (0-1): how busy this area is right now
    relative to its own typical level -- lag_1h vs. rolling_7d_avg from the
    city's multi-month zone mart. >1 means busier than usual."""
    if ctx.pickup_zone_id is None or ctx.city_id not in _ZONE_MODEL_CITIES:
        return None
    momentum = model_service.get_zone_momentum(ctx.pickup_zone_id, ctx.city_id)
    if momentum is None or momentum["rolling_7d_avg"] <= 0:
        return None
    ratio = momentum["lag_1h"] / momentum["rolling_7d_avg"]
    return max(0.0, min(1.0, ratio / 2.0))  # ratio of 2x average maps to full pressure


def predict_availability(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    pressure = _demand_pressure(ctx)
    if pressure is None or features.vehicle_profile is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="availability",
            reason="no demand history for this zone or unrecognized vehicle_class",
        )
    reasons = []
    availability_score = features.vehicle_profile.availability_prior * (1.0 - pressure)
    if ctx.departure_time.weekday() in (4, 5) and ctx.departure_time.hour >= 17:
        availability_score *= 0.85
        reasons.append("weekend/Friday evening demand")
    if features.holiday_score.basis == "computed" and features.holiday_score.value:
        availability_score *= 0.9
        reasons.append("public holiday")
    if features.weather_score.basis == "computed" and features.weather_score.value and features.weather_score.value > 0.4:
        availability_score *= 0.9
        reasons.append("adverse weather")
    if not reasons:
        reasons.append("typical historical demand for this hour")
    bucket = "HIGH" if availability_score > 0.66 else "MEDIUM" if availability_score > 0.33 else "LOW"
    confidence_pct = round(60 + 30 * (1 - pressure), 0)
    return PredictionResult(
        value=bucket, unit=None, basis="modeled_estimate", source="availability_proxy",
        reason=f"confidence {confidence_pct:.0f}% -- " + "; ".join(reasons),
        # Same number the reason string has always quoted, now a real field
        # instead of prose only -- capped at the modeled_estimate ceiling so a
        # proxy can never outscore a measured component.
        confidence=round(min(confidence_pct / 100, BASIS_CONFIDENCE["modeled_estimate"]), 2),
        method="availability_prior_x_demand_pressure",
        score=round(availability_score, 2),
    )


def predict_surge_risk(ctx: JourneyContext, features: JourneyFeatures) -> PredictionResult:
    pressure = _demand_pressure(ctx)
    if pressure is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="surge_risk",
            reason="no demand history for this zone",
        )
    demand_sensitivity = features.vehicle_profile.demand_sensitivity if features.vehicle_profile else 1.0
    risk = min(1.0, pressure * demand_sensitivity)
    if risk < 0.3:
        bucket = "LOW"
    elif risk < 0.55:
        bucket = "MEDIUM"
    elif risk < 0.8:
        bucket = "HIGH"
    else:
        bucket = "VERY_HIGH"
    pct_low, pct_high = round(risk * 20), round(risk * 45)
    return PredictionResult(
        value=bucket, unit=None, basis="modeled_estimate", source="surge_proxy",
        reason=f"expected +{pct_low}% to +{pct_high}% based on current demand momentum vs. zone baseline",
        confidence=BASIS_CONFIDENCE["modeled_estimate"], method="demand_momentum_proxy",
        score=round(risk, 2),
    )


def sweep_best_departure_time(
    pickup_zone_id: int | None, from_hour: int, day_of_week: int, window_hours: int = 6, city_id: str = "nyc",
) -> PredictionResult:
    if pickup_zone_id is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="best_departure_time",
            reason=f"pickup location outside {city_id}'s area coverage",
        )
    candidates = []
    for offset in range(window_hours):
        hour = (from_hour + offset) % 24
        try:
            demand, _ = model_service.predict_demand(pickup_zone_id, hour, day_of_week, city_id=city_id)
        except KeyError:
            continue
        candidates.append((hour, demand))
    if not candidates:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="best_departure_time",
            reason="no demand history for this zone",
        )
    best_hour, _ = min(candidates, key=lambda c: c[1])
    return PredictionResult(
        value=best_hour, unit="hour_of_day", basis="computed", source="demand_sweep_xgboost_demand_v1", reason=None,
        # A sweep over a real trained model, but only over the hours the model
        # actually answered for -- a partial window is a weaker recommendation.
        confidence=round(len(candidates) / window_hours, 2), method="demand_model_sweep",
    )



def predict_confidence(components: dict[str, PredictionResult]) -> PredictionResult:
    """Unchanged semantics -- a plain mean over per-component weights on the
    same 0-1 scale it always used. The only change: a component that carries
    its own `confidence` contributes that instead of its basis default
    (`effective_confidence`). `unavailable` is pinned to 0.0 by
    PredictionResult itself, so a missing component can never raise the
    overall figure."""
    if not components:
        return PredictionResult(value=0.0, unit="percent", basis="computed", source="confidence_engine", reason=None)
    score = sum(effective_confidence(c) for c in components.values()) / len(components)
    return PredictionResult(
        value=round(score * 100, 0), unit="percent", basis="computed", source="confidence_engine", reason=None,
        confidence=round(score, 2), method="mean_component_confidence",
    )
