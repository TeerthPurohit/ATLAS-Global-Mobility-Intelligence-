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

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

logger = logging.getLogger(__name__)

# rag_pipeline.py / nl_to_sql/sql_agent.py are hardcoded to NYC's DuckDB
# warehouse and mart allow-list today (rag/config.py's DEFAULT_DB_PATH) --
# this becomes data-driven once the RAG stack gains per-city routing, which
# is out of scope this phase. Documented limitation, not a fabricated
# per-city capability.
_CHAT_CAPABLE_CITIES = {"nyc"}

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


def get_capabilities(city_id: str) -> dict | None:
    if city_id not in _cities:
        return None
    city = _cities[city_id]
    has_demand = models_registry.resolve_model(city_id, "demand") is not None
    has_fare = models_registry.resolve_model(city_id, "fare") is not None
    capabilities = {
        "mobility_mode": city.get("mobility_mode", "ride_hailing"),
        "area_type": city.get("geography_type", "zone"),
        "demand": has_demand,
        "fare": has_fare,
        "journey": models_registry.resolve_model(city_id, "journey") is not None,
        "chat": city_id in _CHAT_CAPABLE_CITIES,
        "area_analysis": _area_count(city_id) > 0,
        "forecast": has_demand or has_fare,
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


def get_city(city_id: str) -> dict | None:
    city = _cities.get(city_id)
    logger.info("city resolution city_id=%s -> %s", city_id, "found" if city else "not_found")
    return _with_computed_fields(city) if city else None
