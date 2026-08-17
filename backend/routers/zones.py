"""GET /zones (list), GET /zones/{zone_id} (detail) (FR-3).

Zone metadata is static reference data (~265 rows) — loaded once at import
time from data/lookup/zone_centroids.csv (real lat/lon centroids) joined
with the warehouse's taxi_zone_lookup table (borough/service_zone names),
not re-read per request.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
from fastapi import APIRouter, HTTPException
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from algorithms.spatial.kdtree_zone_lookup import load_zone_points  # noqa: E402
from backend.schemas import Zone  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

router = APIRouter(prefix="/zones", tags=["zones"])

_zones: dict[int, Zone] | None = None


def _load_zones() -> dict[int, Zone]:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        lookup = {
            int(location_id): (borough, service_zone)
            for location_id, borough, service_zone in con.execute(
                'select "LocationID", "Borough", service_zone from taxi_zone_lookup'
            ).fetchall()
        }
    finally:
        con.close()

    zones = {}
    for point in load_zone_points():
        borough, service_zone = lookup.get(point.location_id, (None, None))
        zones[point.location_id] = Zone(
            zone_id=point.location_id,
            zone=point.zone,
            borough=borough or "Unknown",
            service_zone=service_zone,
            latitude=point.lat,
            longitude=point.lon,
        )
    return zones


def _get_zones() -> dict[int, Zone]:
    """Lazily build the zone table on first request. Loaded once and cached
    thereafter; a missing/unreadable warehouse degrades to an empty list
    rather than failing the whole app at import time (matching every other
    registry's defensive-load convention)."""
    global _zones
    if _zones is None:
        logger.info("zones step=loading warehouse={}", WAREHOUSE_PATH)
        try:
            _zones = _load_zones()
        except (duckdb.Error, OSError) as exc:  # noqa: BLE001 -- missing warehouse must not kill startup
            logger.warning("zones step=load_zones failed: {} -- serving empty zone list", exc)
            _zones = {}
        else:
            logger.info("zones step=loaded count={}", len(_zones))
    return _zones


@router.get("", response_model=list[Zone], summary="List all NYC TLC zones", description="~265 zones, loaded once at startup.")
def list_zones() -> list[Zone]:
    logger.info("GET /zones step=start")
    zones = list(_get_zones().values())
    logger.info("GET /zones step=done count={}", len(zones))
    return zones


@router.get(
    "/{zone_id}", response_model=Zone, summary="Get one zone",
    responses={400: {"description": "unknown zone_id"}},
)
def get_zone(zone_id: int) -> Zone:
    logger.info("GET /zones/{{id}} step=start zone_id={}", zone_id)
    zone = _get_zones().get(zone_id)
    if zone is None:
        logger.warning("GET /zones/{{id}} step=not_found zone_id={}", zone_id)
        raise HTTPException(status_code=400, detail=f"unknown zone_id={zone_id}")
    logger.info("GET /zones/{{id}} step=done zone_id={}", zone_id)
    return zone
