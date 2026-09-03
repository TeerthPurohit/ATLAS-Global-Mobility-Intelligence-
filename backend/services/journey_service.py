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

import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from algorithms.spatial.kdtree_zone_lookup import load_zone_points  # noqa: E402, I001
from backend.adapters import holidays_nager, routing_osrm, weather_openmeteo  # noqa: E402
from backend.predictors import journey_predictors  # noqa: E402
from backend.predictors.base import JourneyContext, JourneyFeatures, PredictionResult  # noqa: E402
from backend.registry import CITY_ID  # noqa: E402
from backend.services import geography_service, model_service, pricing_engine, vehicle_profiles  # noqa: E402

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
        _baseline_speed_mph = _load_baseline_speed(con)
    finally:
        con.close()


def _load_baseline_speed(con: duckdb.DuckDBPyConnection) -> float | None:
    """Citywide baseline avg_speed_mph, used to turn a zone-pair's historical
    speed into a 0-1 traffic score.

    Prefers the value measured at artifact build time by
    scripts/build_deployed_duckdb.py: the deployed slim warehouse ships no
    int_trips_enriched to scan (ADR-005), and even locally this saves a ~3.5s
    scan of 113M rows on every process start. Falls back to the live scan
    against a full warehouse, and to None when neither is available -- callers
    already skip the traffic score when this is None."""
    try:
        row = con.execute(
            "select value from serving_metadata where key = 'baseline_avg_speed_mph'"
        ).fetchone()
        if row and row[0] is not None:
            precomputed = json.loads(row[0])
            if precomputed is not None:
                return float(precomputed)
    except duckdb.Error:
        pass  # full local warehouse: no serving_metadata table, scan instead

    try:
        row = con.execute(
            "SELECT avg(avg_speed_mph) FROM int_trips_enriched WHERE avg_speed_mph IS NOT NULL"
        ).fetchone()
    except duckdb.Error:
        return None
    return float(row[0]) if row and row[0] is not None else None


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
    pickup_zone_id: int | None, dropoff_zone_id: int | None,
) -> tuple[PredictionResult, PredictionResult, PredictionResult]:
    """Returns (distance, duration, historical_traffic_score)."""
    distance = routing_osrm.fetch_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    duration = routing_osrm.fetch_duration(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)

    hist_duration, hist_speed = (None, None)
    if pickup_zone_id is not None and dropoff_zone_id is not None:
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


def build_context(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    departure_time: datetime, vehicle_type: str,
) -> JourneyContext:
    # resolve() returns None outside the served city's zone coverage, so a
    # coordinate pair anywhere else still degrades every zone-keyed field to
    # an honest `unavailable` rather than snapping to a wrong zone.
    pickup_zone_id = geography_service.resolve(pickup_lat, pickup_lon)
    dropoff_zone_id = geography_service.resolve(dropoff_lat, dropoff_lon)
    return JourneyContext(
        pickup_lat=pickup_lat, pickup_lon=pickup_lon,
        dropoff_lat=dropoff_lat, dropoff_lon=dropoff_lon,
        departure_time=departure_time, vehicle_type=vehicle_type,
        pickup_zone_id=pickup_zone_id, dropoff_zone_id=dropoff_zone_id,
        vehicle_profile=vehicle_profiles.resolve(vehicle_type),
        weather=weather_openmeteo.fetch(pickup_lat, pickup_lon, departure_time),
        holiday=holidays_nager.fetch(pickup_lat, pickup_lon, departure_time),
    )


def build_features(ctx: JourneyContext) -> JourneyFeatures:
    distance, duration, traffic_score = _resolve_distance_duration(
        ctx.pickup_lat, ctx.pickup_lon, ctx.dropoff_lat, ctx.dropoff_lon,
        ctx.pickup_zone_id, ctx.dropoff_zone_id,
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
    departure_time: datetime, vehicle_type: str,
) -> dict[str, PredictionResult]:
    ctx = build_context(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, departure_time, vehicle_type)
    features = build_features(ctx)

    fare_terms = pricing_engine.compute_fare(ctx, features)
    # $12.61 -- the trained fare model's real, measured test-split RMSE
    # (models/fare_prediction/fare_xgb_metadata.json).
    fare_range = journey_predictors.predict_fare_range(fare_terms["total"], test_rmse=12.61)

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
            DEPARTURE_TIME_SWEEP_WINDOW_HOURS,
        ),
    }
    components["confidence"] = journey_predictors.predict_confidence(
        {k: v for k, v in components.items() if k != "confidence"}
    )
    for name, term in fare_terms.items():
        if name != "total":
            components[f"fare_breakdown.{name}"] = term
    components["city_id"] = CITY_ID
    return components
