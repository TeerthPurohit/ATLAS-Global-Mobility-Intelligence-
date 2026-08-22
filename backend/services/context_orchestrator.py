"""Backend Context Orchestrator Service (Phase 4).

Orchestrates environmental, urban, temporal, and capability context for a
registered city (NYC, London -- see ADR-011).

Strict Truth Model Enforcement:
Every context source returns a standardized envelope:
{
    "status": "available" | "unavailable",
    "data": dict | None,
    "source": str,
    "timestamp": str,
    "freshness": str | None,
    "coverage": str | None,
    "reason": str | None,
}
Never fabricates metrics when data sources are unavailable.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.adapters import holidays_nager, routing_osrm, weather_openmeteo  # noqa: E402
from backend.registry import cities as cities_registry  # noqa: E402
from backend.registry import transit as transit_registry  # noqa: E402
from backend.services import model_service, transit_service  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_city_context(city_id: str) -> dict:
    """Orchestrate all available context sources for a city/place."""
    logger.info("context_orchestrator.get_city_context step=start city_id={}", city_id)
    profile = cities_registry.get_city_profile(city_id)
    if not profile:
        logger.warning("context_orchestrator.get_city_context step=profile_unresolvable city_id={}", city_id)
        return {
            "city_id": city_id,
            "city_name": city_id,
            "generated_at": _now_iso(),
            "context": {
                "geography": {
                    "status": "unavailable",
                    "data": None,
                    "source": "city_registry",
                    "timestamp": _now_iso(),
                    "reason": f"unknown or unresolvable city_id={city_id!r}",
                }
            },
        }

    lat = profile["coordinates"].get("latitude")
    lng = profile["coordinates"].get("longitude")
    country_code = profile.get("country_code")
    population = profile.get("population")

    context_map = {}

    # 1. Geography Context
    context_map["geography"] = {
        "status": "available",
        "data": {
            "city": profile["city"],
            "country": profile["country"],
            "country_code": country_code,
            "coordinates": profile["coordinates"],
            "timezone": profile["timezone"],
            "currency": profile["currency"],
            "population": population,
            "place_type": profile["geographic_classification"]["place_type"],
        },
        "source": "city_registry",
        "timestamp": _now_iso(),
        "freshness": "live",
        "coverage": "registered_city",
    }

    # 2. Weather Context
    if lat is not None and lng is not None:
        try:
            weather_res = weather_openmeteo.fetch(lat, lng, datetime.now(timezone.utc))
            if weather_res.basis == "computed":
                context_map["weather"] = {
                    "status": "available",
                    "data": {
                        "temperature": weather_res.value,
                        "unit": weather_res.unit,
                    },
                    "source": weather_res.source,
                    "timestamp": _now_iso(),
                    "freshness": "live",
                    "coverage": "lat_lon_point",
                }
            else:
                context_map["weather"] = {
                    "status": "unavailable",
                    "data": None,
                    "source": weather_res.source,
                    "timestamp": _now_iso(),
                    "reason": weather_res.reason or "weather unavailable for this location",
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("context_orchestrator.get_city_context step=weather failed city_id={} reason={}", city_id, exc)
            context_map["weather"] = {
                "status": "unavailable",
                "data": None,
                "source": "weather_openmeteo",
                "timestamp": _now_iso(),
                "reason": str(exc),
            }
    else:
        context_map["weather"] = {
            "status": "unavailable",
            "data": None,
            "source": "weather_openmeteo",
            "timestamp": _now_iso(),
            "reason": "latitude/longitude unresolvable",
        }

    # 3. Calendar & Holiday Context
    if country_code:
        try:
            today = datetime.now(timezone.utc)
            holiday_res = holidays_nager.fetch(lat or 0.0, lng or 0.0, today, country_code=country_code)
            context_map["calendar"] = {
                "status": "available" if holiday_res.basis == "computed" else "unavailable",
                "data": {
                    "is_holiday": holiday_res.value is True,
                    "details": holiday_res.reason,
                } if holiday_res.basis == "computed" else None,
                "source": holiday_res.source,
                "timestamp": _now_iso(),
                "freshness": "daily",
                "coverage": "national",
                "reason": holiday_res.reason if holiday_res.basis != "computed" else None,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("context_orchestrator.get_city_context step=calendar failed city_id={} reason={}", city_id, exc)
            context_map["calendar"] = {
                "status": "unavailable",
                "data": None,
                "source": "holidays_nager",
                "timestamp": _now_iso(),
                "reason": str(exc),
            }
    else:
        context_map["calendar"] = {
            "status": "unavailable",
            "data": None,
            "source": "holidays_nager",
            "timestamp": _now_iso(),
            "reason": "country_code unresolvable",
        }

    # 4. Urban Density Context
    if population:
        # Real land_area_km2 from the cities seed (Census/ONS-sourced, see
        # dbt_project/seeds/cities.csv).
        registered_city = cities_registry.get_city(city_id)
        land_area_km2 = (registered_city or {}).get("land_area_km2")
        density = round(population / land_area_km2, 1) if land_area_km2 else None
        context_map["urban_density"] = {
            "status": "available",
            "data": {
                "population": population,
                "land_area_km2": land_area_km2,
                "density_per_km2": density,
            },
            "source": "authoritative_census",
            "timestamp": _now_iso(),
            "freshness": "decennial_ons_census",
            "coverage": "metro_area",
        }
    else:
        context_map["urban_density"] = {
            "status": "unavailable",
            "data": None,
            "source": "urban_covariate_registry",
            "timestamp": _now_iso(),
            "reason": "population covariate unresolvable for this location",
        }

    # 5. Routing Capability Context
    try:
        route_check = routing_osrm.fetch_duration(
            lat or 40.7128, lng or -74.0060, (lat or 40.7128) + 0.01, (lng or -74.0060) + 0.01
        )
        context_map["routing"] = {
            "status": "available" if route_check.basis == "computed" else "unavailable",
            "data": {
                "provider": "OSRM",
                "routing_mode": "road_network",
            } if route_check.basis == "computed" else None,
            "source": route_check.source,
            "timestamp": _now_iso(),
            "freshness": "live",
            "coverage": "global_osm",
            "reason": route_check.reason if route_check.basis != "computed" else None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("context_orchestrator.get_city_context step=routing failed city_id={} reason={}", city_id, exc)
        context_map["routing"] = {
            "status": "unavailable",
            "data": None,
            "source": "routing_osrm",
            "timestamp": _now_iso(),
            "reason": str(exc),
        }

    # 6. Mobility Capability Context
    if profile["capabilities"]["observed_mobility"]:
        context_map["mobility_capability"] = {
            "status": "available",
            "data": {"observed_mobility_available": True, "model_status": "active"},
            "source": "atlas_model_registry",
            "timestamp": _now_iso(),
            "freshness": "live",
            "coverage": "platform_registry",
        }
    else:
        context_map["mobility_capability"] = {
            "status": "unavailable",
            "data": None,
            "source": "atlas_model_registry",
            "timestamp": _now_iso(),
            "reason": f"no active demand model registered for city_id={city_id!r}",
        }

    # 6b. Hourly Demand Shape Context -- the city's own real multi-month
    # hour-of-day fractions via model_service.hourly_shape_fraction(), which
    # is what lets chat's LLM narrator answer a "what's the best time to
    # travel" question with a real busiest/quietest hour.
    day_of_week = datetime.now(timezone.utc).weekday()
    hourly = [
        (hour, model_service.hourly_shape_fraction(hour, day_of_week, city_id=city_id))
        for hour in range(24)
    ]
    hourly = [(hour, frac) for hour, frac in hourly if frac is not None]
    if hourly:
        busiest_hour, busiest_frac = max(hourly, key=lambda h: h[1])
        quietest_hour, quietest_frac = min(hourly, key=lambda h: h[1])
        context_map["demand_shape"] = {
            "status": "available",
            "data": {
                "busiest_hour_of_day": busiest_hour,
                "busiest_hour_pct_of_daily_trips": round(busiest_frac * 100, 1),
                "quietest_hour_of_day": quietest_hour,
                "quietest_hour_pct_of_daily_trips": round(quietest_frac * 100, 1),
            },
            "source": "zone_hourly_demand",
            "timestamp": _now_iso(),
            "freshness": "live",
            "coverage": "city_wide_hour_of_day",
        }
    else:
        context_map["demand_shape"] = {
            "status": "unavailable",
            "data": None,
            "source": "model_service.hourly_shape_fraction",
            "timestamp": _now_iso(),
            "reason": "no per-hour demand shape loaded for this city",
        }

    # 7. Transit Coverage Context
    feed = transit_registry.get_feed(city_id)
    if feed is None or not transit_registry.has_feed(city_id):
        context_map["transit_coverage"] = {
            "status": "unavailable",
            "data": None,
            "source": "gtfs_feeds_registry",
            "timestamp": _now_iso(),
            "reason": f"no ingested GTFS feed for city_id={city_id!r}",
        }
    elif lat is not None and lng is not None:
        stop_count = transit_service.count_stops_near(city_id, lat, lng, radius_km=5.0)
        context_map["transit_coverage"] = {
            "status": "available" if stop_count is not None else "unavailable",
            "data": {"agency_name": feed["agency_name"], "stop_count": stop_count, "radius_km": 5.0} if stop_count is not None else None,
            "source": feed["agency_name"],
            "timestamp": _now_iso(),
            "freshness": "static_reference_data",
            "coverage": "point_radius",
            "reason": None if stop_count is not None else "no gtfs_stops rows loaded for this city yet",
        }
    else:
        context_map["transit_coverage"] = {
            "status": "unavailable",
            "data": None,
            "source": "gtfs_feeds_registry",
            "timestamp": _now_iso(),
            "reason": "latitude/longitude unresolvable",
        }

    logger.info("context_orchestrator.get_city_context step=done city_id={} sources={}", city_id, list(context_map))
    return {
        "city_id": profile["city_id"],
        "city_name": profile["city"],
        "generated_at": _now_iso(),
        "context": context_map,
    }
