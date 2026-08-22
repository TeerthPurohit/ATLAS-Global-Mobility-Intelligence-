"""City registry (SPEC-013 FR-4) -- thin query module over the seeded
`cities` dbt table, loaded once at startup (rule 8: one real row today).

`capabilities` and `metrics` are deliberately NOT seed columns (they'd drift
from reality) -- computed here from what's actually wired: `backend.registry
.models` (real model_registry rows) for demand/fare/journey,
`backend.services.geography_service` (real canonical_areas rows) for
area_analysis. `model_status` is likewise recomputed from live model_registry
rows rather than trusted verbatim from the seed, so a future city (e.g.
London, SPEC-015) flips to "active" automatically once its models actually
land -- zero code change here.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

from backend.registry import models as models_registry
from backend.registry import transit as transit_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

logger = logging.getLogger(__name__)

# Chat tier is a pure function of two real infrastructure facts, not a
# curated allowlist: does this city have a registered, queryable warehouse
# (needed for any SQL-grounded answer at all), and does it have a generated
# insight-doc corpus for vector RAG. London's station-level corpus was
# generated 2026-08-14 (rag/insight_generation/generate_london_insight_docs.py,
# embedded into the "insight_docs_london" Qdrant collection -- see
# backend/services/rag_service.py's _CITY_INSIGHT_COLLECTION). Adding a
# further city's real chat capability means registering its warehouse path
# (infrastructure it needs anyway for predictions/journey) and, optionally,
# generating its insight docs -- never a chat-specific code change here.
_CITY_WAREHOUSE_PATHS = {
    "nyc": REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb",
    "london": REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb",
}
_CITY_HAS_INSIGHT_DOCS = {"nyc", "london"}


def get_chat_tier(city_id: str) -> str:
    if city_id not in _CITY_WAREHOUSE_PATHS:
        return "context_only"
    return "full_rag" if city_id in _CITY_HAS_INSIGHT_DOCS else "sql_only"

_CITY_COLUMNS = (
    "id", "name", "country_code", "latitude", "longitude", "timezone",
    "currency", "status", "data_source", "geography_type", "model_status", "last_updated",
)


_cities: dict[str, dict] = {}


def load() -> None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        df = con.execute("select * from cities").df()
    finally:
        con.close()
    _cities.clear()
    for _, row in df.iterrows():
        city = row.to_dict()
        city["last_updated"] = str(city["last_updated"])  # duckdb types the seed column as DATE
        _cities[city["id"]] = city



def _effective_model_status(city_id: str, seed_status: str) -> str:
    if models_registry.has_active_model(city_id):
        return "active"
    return "unavailable" if seed_status == "active" else seed_status


def _area_count(city_id: str) -> int:
    from backend.services import geography_service  # local import: avoids a hard import-order dependency at module load

    return len(geography_service.list_areas(city_id))


JOURNEY_CAPABILITIES: tuple[str, ...] = (
    "routing", "demand", "fare", "congestion", "availability", "surge", "carbon", "best_departure",
)


def capability_matrix(city_id: str) -> dict[str, bool] | None:
    """Per-journey-field support for a registered city, derived from what's
    actually wired. A fare needs a trained fare model OR a real tariff profile
    keyed by this exact city_id, nothing else.

    Returns None for a city_id this registry doesn't know.
    """
    from backend.services import tariff_profiles

    registered = get_city(city_id)
    if registered is None:
        return None

    # Zone-level predictors (availability/surge/best_departure/congestion's
    # traffic leg) all bottom out in model_service's per-city zone marts,
    # which only exist for a city with an active demand model.
    has_zone_model = models_registry.resolve_model(city_id, "demand") is not None
    has_fare_model = models_registry.resolve_model(city_id, "fare") is not None

    return {
        # OSRM (with a haversine fallback) routes between the coordinates the
        # request itself carries -- no per-city data needed, so this is true
        # for every resolvable city, same as carbon.
        "routing": True,
        "demand": has_zone_model,
        "fare": has_fare_model or tariff_profiles.get(city_id) is not None,
        # predict_congestion fuses a historical-traffic leg (zone-model cities
        # only) with a weather leg the Open-Meteo adapter serves from the
        # request's own coordinates -- one leg is enough for a bucket.
        "congestion": True,
        "availability": has_zone_model,
        "surge": has_zone_model,
        "carbon": True,  # distance x seeded emission factor, city-independent
        "best_departure": has_zone_model,
    }


def get_capabilities(city_id: str) -> dict | None:
    matrix = capability_matrix(city_id)
    if matrix is None:
        return None
    city = _cities.get(city_id, {})
    registered = city_id in _cities
    has_demand = models_registry.resolve_model(city_id, "demand") is not None
    has_fare = matrix["fare"]
    capabilities = {
        "mobility_mode": city.get("mobility_mode", "ride_hailing"),
        "area_type": city.get("geography_type", "zone"),
        "demand": has_demand,
        "fare": has_fare,
        # journey_predictors.py orchestrates routing/demand/fare/carbon/
        # congestion/availability/surge/best_departure with per-component
        # honest degradation (never a hard failure) -- POST /journey/estimate
        # already returns 200 for any resolvable city (verified live for
        # nyc/Marseille/Tokyo/Liverpool, /debug 2026-08-13). The
        # model_registry lookup this used to gate on only ever had one row,
        # for nyc, which made this flag False for every other city even
        # though the endpoint it describes works the same way everywhere.
        "journey": True,
        # Every resolvable city gets SOME chat tier (context_only is a real,
        # working answer path -- _answer_context_only() narrates over real
        # geography/weather/demand-shape context, grounded and non-fabricating,
        # see rag_service.py's _CONTEXT_ONLY_SYSTEM_PROMPT). This used to read
        # `!= "context_only"`, which reported every non-nyc/london city as
        # chat-incapable even though it could genuinely answer questions --
        # confusing "not the best tier" with "no chat at all" (found via
        # /debug 2026-08-13).
        "chat": True,
        "chat_tier": get_chat_tier(city_id),
        # canonical_areas now has real WorldMove grid_cell rows for every
        # covered city (SPEC-016), not just nyc/london zones/stations -- the
        # `registered and` gate here predates that and made area_analysis
        # always False for a real, non-empty area count.
        "area_analysis": _area_count(city_id) > 0,
        "forecast": has_demand or has_fare,
        "transit_coverage": transit_registry.has_feed(city_id),
        **matrix,
    }
    logger.info("capability check city_id=%s -> %s", city_id, capabilities)
    return capabilities


def list_metrics(city_id: str) -> list[str]:
    capabilities = get_capabilities(city_id) or {}
    return [metric for metric in ("demand", "fare", "journey") if capabilities.get(metric)]


def _with_computed_fields(city: dict) -> dict:
    return {**city, "model_status": _effective_model_status(city["id"], city["model_status"])}


def list_cities(country_code: str | None = None) -> list[dict]:
    rows = _cities.values()
    if country_code:
        rows = [c for c in rows if c["country_code"] == country_code.upper()]
    return [_with_computed_fields(c) for c in rows]


def get_city_profile(city_id: str) -> dict | None:
    """Authoritative geographic facts for a registered city (ADR-011).

    Was `global_geography_service.get_city_profile`, whose other two branches
    (the 524-row WorldMove registry and a live GeoNames search) are gone with
    the global layer. Every city this repo serves is now a row in the `cities`
    seed with real trip data behind it, so there is nothing left to resolve --
    `model_status`/`confidence` are no longer tier estimates but statements
    about a city we actually measured.
    """
    registered = get_city(city_id)
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
                                     # up for these seeded rows, so this doesn't claim one.
            "place_type": "city",
        },
        "capabilities": {
            "geographic": True,
            "context": True,
            "observed_mobility": (get_capabilities(city_id) or {}).get("demand", False),
        },
        "model_status": "OBSERVED",
        "confidence": 1.0,
    }


def get_city(city_id: str) -> dict | None:
    if not _cities:
        # Defensive lazy-load: real traffic always goes through the FastAPI
        # lifespan hook (backend/main.py), which calls load() before serving
        # requests, so this never fires in production. It matters for tests
        # that exercise this module directly without that startup event --
        # without it, an empty registry silently reads as "city not found"
        # and callers (e.g. global_geography_service) fall through to
        # treating a real, registered city_id as a free-text search query.
        load()
    city = _cities.get(city_id)
    logger.info("city resolution city_id=%s -> %s", city_id, "found" if city else "not_found")
    return _with_computed_fields(city) if city else None
