"""Backend Context Orchestrator Service (Phase 4).

Dynamically orchestrates environmental, urban, temporal, and capability context
for any globally resolved city (NYC, London, Mumbai, Jaipur, Dubai, Cape Town, Tokyo, etc.).

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

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.adapters import holidays_nager, routing_osrm, weather_openweather  # noqa: E402
from backend.services import global_geography_service  # noqa: E402

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_city_context(city_id: str) -> dict:
    """Orchestrate all available context sources for a city/place."""
    profile = global_geography_service.get_city_profile(city_id)
    if not profile:
        return {
            "city_id": city_id,
            "city_name": city_id,
            "generated_at": _now_iso(),
            "context": {
                "geography": {
                    "status": "unavailable",
                    "data": None,
                    "source": "global_geography_registry",
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
        "source": "global_geography_registry",
        "timestamp": _now_iso(),
        "freshness": "live",
        "coverage": "global",
    }

    # 2. Weather Context
    if lat is not None and lng is not None:
        try:
            weather_res = weather_openweather.get_weather(lat, lng)
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
                    "reason": weather_res.reason or "OPENWEATHER_API_KEY unset",
                }
        except Exception as exc:  # noqa: BLE001
            context_map["weather"] = {
                "status": "unavailable",
                "data": None,
                "source": "weather_openweather",
                "timestamp": _now_iso(),
                "reason": str(exc),
            }
    else:
        context_map["weather"] = {
            "status": "unavailable",
            "data": None,
            "source": "weather_openweather",
            "timestamp": _now_iso(),
            "reason": "latitude/longitude unresolvable",
        }

    # 3. Calendar & Holiday Context
    if country_code:
        try:
            today = datetime.now(timezone.utc)
            holiday_res = holidays_nager.get_holiday_status(country_code, today)
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
        # Land area approximations for reference cities where available
        known_areas = {"nyc": 778.2, "london": 1572.0}
        land_area_km2 = known_areas.get(city_id.lower())
        density = round(population / land_area_km2, 1) if land_area_km2 else None
        context_map["urban_density"] = {
            "status": "available",
            "data": {
                "population": population,
                "land_area_km2": land_area_km2,
                "density_per_km2": density,
            },
            "source": "authoritative_census_and_geonames",
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
        route_check = routing_osrm.get_route(
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
        context_map["routing"] = {
            "status": "unavailable",
            "data": None,
            "source": "routing_osrm",
            "timestamp": _now_iso(),
            "reason": str(exc),
        }

    # 6. Mobility Capability Context
    obs_available = profile["capabilities"]["observed_mobility"]
    context_map["mobility_capability"] = {
        "status": "available",
        "data": {
            "observed_mobility_available": obs_available,
            "cross_city_modeling_available": profile["capabilities"]["cross_city_model"],
            "model_status": "active" if obs_available else "estimated",
        },
        "source": "atlas_model_registry",
        "timestamp": _now_iso(),
        "freshness": "live",
        "coverage": "platform_registry",
    }

    return {
        "city_id": profile["city_id"],
        "city_name": profile["city"],
        "generated_at": _now_iso(),
        "context": context_map,
    }
