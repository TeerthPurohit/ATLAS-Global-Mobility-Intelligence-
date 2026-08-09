"""Journey orchestration (ADR-007 §6): JourneyContext -> build_features ->
a fixed predictor sequence -> JourneyEstimate. A plain ordered sequence of
calls, not a generic dependency-graph executor -- right-sized for ~10 known
predictors (see the plan's reasoning for not building a DAG framework here).

`load()` runs once at FastAPI startup (rule 8): it computes the citywide
baseline speed used to turn a zone-pair's historical avg_speed_mph into a
0-1 traffic score, and builds the zone_id -> zone_name map the mart lookups
need. Nothing in the request path re-scans the warehouse.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from algorithms.spatial.kdtree_zone_lookup import load_zone_points  # noqa: E402
from backend.adapters import holidays_nager, routing_osrm, weather_openmeteo  # noqa: E402
from backend.predictors import journey_predictors  # noqa: E402
from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult  # noqa: E402
from backend.services import geography_service, global_geography_service, model_service, pricing_engine, vehicle_profiles  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
DEPARTURE_TIME_SWEEP_WINDOW_HOURS = 6

_zone_names: dict[int, str] = {}
_baseline_speed_mph: float | None = None


def load() -> None:
    global _baseline_speed_mph
    vehicle_profiles.load()
    _zone_names.clear()
    for point in load_zone_points():
        _zone_names[point.location_id] = point.zone

    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        row = con.execute("SELECT avg(avg_speed_mph) FROM int_trips_enriched WHERE avg_speed_mph IS NOT NULL").fetchone()
    finally:
        con.close()
    _baseline_speed_mph = float(row[0]) if row and row[0] is not None else None


def _historical_pair(pickup_zone_id: int, dropoff_zone_id: int) -> tuple[float | None, float | None]:
    """Real historical (avg_duration_min, avg_speed_mph) for this exact
    zone-name pair from the zone_pair_flows mart. Direct-pair only -- no
    multi-hop fallback in this phase (ponytail: upgrade path is Dijkstra
    over algorithms/graph/shortest_path_eta.py's graph if a pair with no
    direct trips turns out to matter in practice)."""
    pickup_name = _zone_names.get(pickup_zone_id)
    dropoff_name = _zone_names.get(dropoff_zone_id)
    if pickup_name is None or dropoff_name is None:
        return None, None
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        row = con.execute(
            "SELECT sum(avg_duration_min * trip_count) / sum(trip_count), "
            "       sum(avg_speed_mph * trip_count) / sum(trip_count) "
            "FROM zone_pair_flows WHERE pickup_zone = ? AND dropoff_zone = ? AND trip_count > 0",
            [pickup_name, dropoff_name],
        ).fetchone()
    finally:
        con.close()
    if row is None or row[0] is None:
        return None, None
    return float(row[0]), float(row[1]) if row[1] is not None else None


def _resolve_distance_duration(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    pickup_zone_id: int | None, dropoff_zone_id: int | None, city_id: str,
) -> tuple[PredictionResult, PredictionResult, PredictionResult]:
    """Returns (distance, duration, historical_traffic_score)."""
    distance = routing_osrm.fetch_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    duration = routing_osrm.fetch_duration(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)

    # zone_pair_flows/_zone_names are NYC-only (built from NYC's
    # zone_centroids.csv) -- a London/other-city zone/station id is a small
    # int too and could otherwise collide with an unrelated NYC zone id.
    hist_duration, hist_speed = (None, None)
    if city_id == "nyc" and pickup_zone_id is not None and dropoff_zone_id is not None:
        hist_duration, hist_speed = _historical_pair(pickup_zone_id, dropoff_zone_id)

    if distance.basis == "unavailable":
        miles = model_service.haversine_miles((pickup_lat, pickup_lon), (dropoff_lat, dropoff_lon))
        distance = PredictionResult(value=round(miles, 2), unit="miles", basis="computed", source="haversine", reason=None)

    if duration.basis == "unavailable":
        if hist_duration is not None:
            duration = PredictionResult(
                value=round(hist_duration, 1), unit="minutes", basis="computed", source="zone_pair_flows", reason=None,
            )
        else:
            duration = PredictionResult(
                value=None, unit=None, basis="unavailable", source="duration",
                reason="OSRM unavailable and no direct historical trips for this zone pair",
            )

    if hist_speed is not None and _baseline_speed_mph:
        score = max(0.0, min(1.0, (_baseline_speed_mph - hist_speed) / _baseline_speed_mph))
        traffic_score = PredictionResult(
            value=round(score, 2), unit="score_0_to_1", basis="computed", source="zone_pair_flows_vs_citywide_baseline",
            reason=None,
        )
    else:
        traffic_score = PredictionResult(
            value=None, unit=None, basis="unavailable", source="historical_traffic_score",
            reason="no direct historical trips for this zone pair",
        )
    return distance, duration, traffic_score


_UNRESOLVED_CITY = "unresolved"


def _resolve_city_id(pickup_lat: float, pickup_lon: float, city_id: str | None) -> str:
    """Explicit `city_id` wins (normalized through global_geography_service
    so "mumbai" and its GeoNames id always resolve to the same
    city_tariff_profiles row). Otherwise NYC/London bbox auto-detection --
    same behavior every caller had before city_id existed. Anywhere else, a
    bare lat/lon pair alone doesn't uniquely identify a city worth caching a
    tariff profile for -- resolves to a sentinel that carries no zone/tariff
    coverage, so every city-scoped field honestly degrades to `unavailable`
    (same "degrade honestly, never fabricate" contract as an unrecognized
    vehicle_type) rather than erroring out. The caller should pass city_id
    explicitly whenever it's known (the frontend's city picker always does)."""
    if city_id:
        profile = global_geography_service.get_city_profile(city_id)
        return profile["city_id"] if profile else city_id
    detected = geography_service.detect_city_from_coords(pickup_lat, pickup_lon)
    return detected or _UNRESOLVED_CITY


def build_context(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    departure_time: datetime, vehicle_type: str, city_id: str | None = None,
) -> JourneyContext:
    resolved_city_id = _resolve_city_id(pickup_lat, pickup_lon, city_id)
    pickup_zone_id = geography_service.resolve_for_city(resolved_city_id, pickup_lat, pickup_lon)
    dropoff_zone_id = geography_service.resolve_for_city(resolved_city_id, dropoff_lat, dropoff_lon)
    return JourneyContext(
        pickup_lat=pickup_lat, pickup_lon=pickup_lon,
        dropoff_lat=dropoff_lat, dropoff_lon=dropoff_lon,
        departure_time=departure_time, vehicle_type=vehicle_type,
        pickup_zone_id=pickup_zone_id, dropoff_zone_id=dropoff_zone_id,
        vehicle_profile=vehicle_profiles.resolve(vehicle_type),
        weather=weather_openmeteo.fetch(pickup_lat, pickup_lon, departure_time),
        holiday=holidays_nager.fetch(pickup_lat, pickup_lon, departure_time),
        city_id=resolved_city_id,
    )


def build_features(ctx: JourneyContext) -> JourneyFeatures:
    distance, duration, traffic_score = _resolve_distance_duration(
        ctx.pickup_lat, ctx.pickup_lon, ctx.dropoff_lat, ctx.dropoff_lon,
        ctx.pickup_zone_id, ctx.dropoff_zone_id, ctx.city_id,
    )
    return JourneyFeatures(
        distance_miles=distance,
        duration_min=duration,
        weather_score=ctx.weather,
        holiday_score=ctx.holiday,
        historical_traffic_score=traffic_score,
        vehicle_profile=ctx.vehicle_profile,
    )


def estimate(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    departure_time: datetime, vehicle_type: str, city_id: str | None = None,
) -> dict[str, PredictionResult]:
    ctx = build_context(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, departure_time, vehicle_type, city_id)
    features = build_features(ctx)

    fare_terms = pricing_engine.compute_fare(ctx, features)
    if ctx.city_id == "nyc":
        # $12.61 -- the trained fare model's real, measured test-split RMSE
        # (models/fare_prediction/fare_xgb_metadata.json).
        fare_range = journey_predictors.predict_fare_range(fare_terms["total"], test_rmse=12.61)
    else:
        fare_range = journey_predictors.predict_fare_range(fare_terms["total"], fraction=pricing_engine.CALIBRATION_MAPE_PCT)

    components: dict[str, PredictionResult] = {
        "distance": features.distance_miles,
        "duration": features.duration_min,
        "fare": fare_terms["total"],
        "fare_range": fare_range,
        "demand": journey_predictors.predict_demand(ctx, features),
        "carbon_emissions": journey_predictors.predict_carbon(features),
        "congestion": journey_predictors.predict_congestion(features),
        "ride_availability": journey_predictors.predict_availability(ctx, features),
        "surge_risk": journey_predictors.predict_surge_risk(ctx, features),
        "best_departure_time": journey_predictors.sweep_best_departure_time(
            ctx.pickup_zone_id, departure_time.hour, departure_time.weekday(),
            DEPARTURE_TIME_SWEEP_WINDOW_HOURS, city_id=ctx.city_id,
        ),
    }
    components["confidence"] = journey_predictors.predict_confidence(
        {k: v for k, v in components.items() if k != "confidence"}
    )
    for name, term in fare_terms.items():
        if name != "total":
            components[f"fare_breakdown.{name}"] = term
    components["city_id"] = ctx.city_id
    return components
