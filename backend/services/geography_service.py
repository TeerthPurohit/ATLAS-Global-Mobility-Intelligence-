"""Geography domain (ADR-007 candidate for Phase 2's Region generalization;
Phase 1 keeps the existing NYC `Zone`/`zone_id` schema as-is).

One job: `resolve(lat, lon) -> zone_id | None`, a thin wrapper around the
existing KD-tree zone lookup (`algorithms/spatial/kdtree_zone_lookup.py`).
`None` means "outside NYC's zone coverage" -- every zone-keyed predictor
degrades honestly to `basis="unavailable"` for that component rather than
snapping a non-NYC coordinate to the nearest NYC zone, which would silently
fabricate a wrong answer for the "global means degrading honestly" design
principle in the plan.

SPEC-013 FR-5 adds `list_areas(city_id)` / `get_area(city_id, area_id)`,
backed by the `canonical_areas` mart -- a distinct concern from the
nearest-neighbor `resolve()` above (listing a city's areas vs. resolving a
coordinate to one), so it's read straight from DuckDB rather than routed
through the KD-tree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

from algorithms.spatial.kdtree_zone_lookup import KDTree, ZonePoint, load_zone_points  # noqa: E402

# NYC's real zone-coverage bounding box, same bounds used by
# kdtree_zone_lookup.py's own benchmark_summary() for synthetic NYC queries.
_NYC_BBOX = (40.49, -74.26, 40.92, -73.68)  # (min_lat, min_lon, max_lat, max_lon)
# Greater London's real administrative extent (commonly cited bounds).
_LONDON_BBOX = (51.28, -0.51, 51.70, 0.33)

_tree: KDTree | None = None
_london_tree: KDTree | None = None

_AREA_COLUMNS = ("area_id", "city_id", "name", "area_type", "parent_area_id", "latitude", "longitude")


def _get_tree() -> KDTree:
    global _tree
    if _tree is None:
        _tree = KDTree(load_zone_points())
    return _tree


def load_london_station_points() -> list[ZonePoint]:
    """Same ZonePoint shape as NYC's zone_centroids loader, sourced from the
    canonical_areas mart's London rows (real station coordinates) instead of
    a CSV -- London's centroids only exist in the mart, not a lookup file."""
    return [
        ZonePoint(location_id=a["area_id"], zone=a["name"], lat=a["latitude"], lon=a["longitude"])
        for a in list_areas("london")
        if a["latitude"] is not None and a["longitude"] is not None
    ]


def _get_london_tree() -> KDTree:
    global _london_tree
    if _london_tree is None:
        _london_tree = KDTree(load_london_station_points())
    return _london_tree


def in_coverage(lat: float, lon: float) -> bool:
    min_lat, min_lon, max_lat, max_lon = _NYC_BBOX
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def _in_london_coverage(lat: float, lon: float) -> bool:
    min_lat, min_lon, max_lat, max_lon = _LONDON_BBOX
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def resolve(lat: float, lon: float) -> int | None:
    if not in_coverage(lat, lon):
        return None
    point = _get_tree().nearest(lat, lon)
    return point.location_id if point else None


def detect_city_from_coords(lat: float, lon: float) -> str | None:
    """NYC/London bbox detection for a journey request that didn't specify
    city_id explicitly -- None means "no zone-enriched city recognizes this
    point," not "no city exists here" (the caller falls back to reverse
    geocoding via global_geography_service for anywhere else on Earth)."""
    if in_coverage(lat, lon):
        return "nyc"
    if _in_london_coverage(lat, lon):
        return "london"
    return None


def resolve_for_city(city_id: str, lat: float, lon: float) -> int | None:
    """Like resolve(), generalized to any city with a real zone/station KD-tree.
    None means "outside this city's coverage" -- never snaps to the nearest
    point regardless of distance, same honesty discipline as resolve()."""
    if city_id == "nyc":
        return resolve(lat, lon)
    if city_id == "london":
        if not _in_london_coverage(lat, lon):
            return None
        point = _get_london_tree().nearest(lat, lon)
        return point.location_id if point else None
    return None  # no zone/station coverage for any other city yet


def list_areas(city_id: str) -> list[dict]:
    """Real rows from the `canonical_areas` mart -- a small (~265 for NYC)
    dimension read, not a table scan (rule 8)."""
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        rows = con.execute(
            f"select {', '.join(_AREA_COLUMNS)} from canonical_areas where city_id = ? order by area_id",
            [city_id],
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(_AREA_COLUMNS, r)) for r in rows]


def get_area(city_id: str, area_id: int) -> dict | None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        row = con.execute(
            f"select {', '.join(_AREA_COLUMNS)} from canonical_areas where city_id = ? and area_id = ?",
            [city_id, area_id],
        ).fetchone()
    finally:
        con.close()
    return dict(zip(_AREA_COLUMNS, row)) if row else None
