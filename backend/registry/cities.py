"""City registry -- thin query module over the seeded `cities` dbt table,
loaded once at startup (rule 8). One real row, `nyc` (ADR-012), and as of
ADR-013 nothing above this module passes a city id at all.

`capabilities` and `metrics` are deliberately NOT seed columns (they'd drift
from reality) -- computed here from what's actually wired: `backend.registry
.models` (real model_registry rows) for demand/fare/journey,
`backend.services.geography_service` (real canonical_areas rows) for
area_analysis. `model_status` is likewise recomputed from live model_registry
rows rather than trusted verbatim from the seed, so the city flips to
"active" automatically once its models actually land -- zero code change here.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

from backend.registry import CITY_ID
from backend.registry import models as models_registry
from backend.registry import transit as transit_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

logger = logging.getLogger(__name__)

# Chat tier is a pure function of one real infrastructure fact, not a
# curated allowlist: does this city have a generated insight-doc corpus for
# vector RAG on top of its (always present) queryable warehouse.
_HAS_INSIGHT_DOCS = True


def get_chat_tier() -> str:
    """`full_rag` with both a warehouse and an insight corpus, `sql_only`
    with a warehouse alone."""
    return "full_rag" if _HAS_INSIGHT_DOCS else "sql_only"


_city: dict | None = None


def load() -> None:
    global _city
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        df = con.execute("select * from cities").df()
    finally:
        con.close()
    rows = [r.to_dict() for _, r in df.iterrows() if r.to_dict()["id"] == CITY_ID]
    if not rows:
        logger.warning("cities seed has no %s row; the registry will read as unconfigured", CITY_ID)
        _city = None
        return
    city = rows[0]
    city["last_updated"] = str(city["last_updated"])  # duckdb types the seed column as DATE
    _city = city


def _effective_model_status(seed_status: str) -> str:
    if models_registry.has_active_model():
        return "active"
    return "unavailable" if seed_status == "active" else seed_status


def _area_count() -> int:
    from backend.services import geography_service  # local import: avoids a hard import-order dependency at module load

    return len(geography_service.list_areas())


JOURNEY_CAPABILITIES: tuple[str, ...] = (
    "routing", "demand", "fare", "congestion", "availability", "surge", "carbon", "best_departure",
)


def capability_matrix() -> dict[str, bool] | None:
    """Per-journey-field support, derived from what's actually wired. A fare
    needs a trained fare model OR a real tariff profile, nothing else.

    Returns None when the registry has no city row at all (a broken seed),
    which callers surface rather than papering over.
    """
    from backend.services import tariff_profiles

    if get_city() is None:
        return None

    # Zone-level predictors (availability/surge/best_departure/congestion's
    # traffic leg) all bottom out in model_service's zone marts, which only
    # exist with an active demand model.
    has_zone_model = models_registry.resolve_model("demand") is not None
    has_fare_model = models_registry.resolve_model("fare") is not None

    return {
        # OSRM (with a haversine fallback) routes between the coordinates the
        # request itself carries -- no stored data needed, same as carbon.
        "routing": True,
        "demand": has_zone_model,
        "fare": has_fare_model or tariff_profiles.get() is not None,
        # predict_congestion fuses a historical-traffic leg with a weather leg
        # the Open-Meteo adapter serves from the request's own coordinates --
        # one leg is enough for a bucket.
        "congestion": True,
        "availability": has_zone_model,
        "surge": has_zone_model,
        "carbon": True,  # distance x seeded emission factor
        "best_departure": has_zone_model,
    }


def get_capabilities() -> dict | None:
    matrix = capability_matrix()
    if matrix is None:
        return None
    city = _city or {}
    has_demand = models_registry.resolve_model("demand") is not None
    has_fare = matrix["fare"]
    capabilities = {
        "mobility_mode": city.get("mobility_mode", "ride_hailing"),
        "area_type": city.get("geography_type", "zone"),
        "demand": has_demand,
        "fare": has_fare,
        # journey_predictors.py orchestrates routing/demand/fare/carbon/
        # congestion/availability/surge/best_departure with per-component
        # honest degradation, never a hard failure.
        "journey": True,
        # The warehouse is always there, so a SQL-grounded question can always
        # be answered -- the tier says how well, not whether.
        "chat": True,
        "chat_tier": get_chat_tier(),
        "area_analysis": _area_count() > 0,
        "forecast": has_demand or has_fare,
        "transit_coverage": transit_registry.has_feed(),
        **matrix,
    }
    logger.info("capability check -> %s", capabilities)
    return capabilities


def list_metrics() -> list[str]:
    capabilities = get_capabilities() or {}
    return [metric for metric in ("demand", "fare", "journey") if capabilities.get(metric)]


def _with_computed_fields(city: dict) -> dict:
    return {**city, "model_status": _effective_model_status(city["model_status"])}


def get_city_profile() -> dict | None:
    """Authoritative geographic facts for the served city (ADR-011).

    Was `global_geography_service.get_city_profile`, whose other two branches
    (the 524-row WorldMove registry and a live GeoNames search) are gone with
    the global layer. The city this repo serves is a row in the `cities` seed
    with real trip data behind it, so there is nothing left to resolve --
    `model_status`/`confidence` are no longer tier estimates but statements
    about a city we actually measured.
    """
    registered = get_city()
    if registered is None:
        return None
    return {
        "city_id": registered["id"],
        "city": registered["name"],
        "country": registered.get("country_code"),
        "country_code": registered.get("country_code"),
        "coordinates": {
            "latitude": registered.get("latitude"),
            "longitude": registered.get("longitude"),
        },
        "timezone": registered.get("timezone", "UTC"),
        "currency": registered.get("currency", "USD"),
        "population": registered.get("population"),
        "administrative_hierarchy": [
            {"name": registered["name"], "type": "city"},
            {"name": registered.get("country_code"), "type": "country"},
        ],
        "alternate_names": [registered["name"]],
        "geographic_classification": {
            "feature_class": "P",
            "feature_code": "PPL",  # generic "populated place" -- a real per-city GeoNames
                                     # feature code (e.g. PPLC for a capital) was never looked
                                     # up for this seeded row, so this doesn't claim one.
            "place_type": "city",
        },
        "capabilities": {
            "geographic": True,
            "context": True,
            "observed_mobility": (get_capabilities() or {}).get("demand", False),
        },
        "model_status": "OBSERVED",
        "confidence": 1.0,
    }


def get_city() -> dict | None:
    if _city is None:
        # Defensive lazy-load: real traffic always goes through the FastAPI
        # lifespan hook (backend/main.py), which calls load() before serving
        # requests, so this never fires in production. It matters for tests
        # that exercise this module directly without that startup event.
        load()
    return _with_computed_fields(_city) if _city else None
