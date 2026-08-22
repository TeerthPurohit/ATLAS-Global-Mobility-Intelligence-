"""Correctness checks for the map hero's zone geometry (ADR-011 phase 7).

The bug this guards against actually happened: `ST_Transform` to EPSG:4326
emits (lat, lon) by default, because that is EPSG:4326's formal axis order.
GeoJSON requires (lon, lat). Without `always_xy := true` in
scripts/build_zone_geojson.py, every zone silently lands off the coast of
Africa -- valid JSON, valid GeoJSON, renders a blank map.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "lookup" / "taxi_zones.geojson"

# NYC's real extent, padded. Newark Airport (zone 1) is the western outlier.
NYC_LON_RANGE = (-74.3, -73.6)
NYC_LAT_RANGE = (40.4, 41.0)


def _coords(node):
    """Walk an arbitrarily nested GeoJSON coordinate array down to positions."""
    if isinstance(node[0], (int, float)):
        yield node
    else:
        for child in node:
            yield from _coords(child)


@pytest.fixture(scope="module")
def zones() -> dict:
    if not GEOJSON_PATH.exists():
        pytest.skip(f"{GEOJSON_PATH.name} not built -- run scripts/build_zone_geojson.py")
    return json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))


def test_every_zone_position_is_lon_lat_inside_nyc(zones):
    """Catches the axis-order bug: (lat, lon) puts NYC at ~(40, -74) read as
    lon=40, lat=-74 -- the Indian Ocean, off Antarctica."""
    positions = [p for f in zones["features"] for p in _coords(f["geometry"]["coordinates"])]
    assert positions, "no coordinates in the file at all"

    lons = [p[0] for p in positions]
    lats = [p[1] for p in positions]
    assert NYC_LON_RANGE[0] < min(lons) and max(lons) < NYC_LON_RANGE[1], (
        f"longitude range {min(lons):.3f}..{max(lons):.3f} is outside NYC -- "
        "likely (lat, lon) axis order; see always_xy in build_zone_geojson.py"
    )
    assert NYC_LAT_RANGE[0] < min(lats) and max(lats) < NYC_LAT_RANGE[1], (
        f"latitude range {min(lats):.3f}..{max(lats):.3f} is outside NYC"
    )


def test_location_ids_join_to_the_zone_lookup(zones):
    """The choropleth joins these to zone_hourly_demand on location_id -- a
    drifted or missing id renders that zone unshaded rather than erroring."""
    ids = [f["properties"]["location_id"] for f in zones["features"]]
    assert len(ids) == len(set(ids)), "duplicate location_id in the geometry"
    assert min(ids) >= 1 and max(ids) <= 265, f"location_id out of TLC range: {min(ids)}..{max(ids)}"
    # 263, not 265: the TLC shapefile has no polygon for 264/265 ("Unknown").
    assert len(ids) == 263, f"expected 263 zone polygons, got {len(ids)}"


def test_every_feature_carries_the_properties_the_map_reads(zones):
    for feature in zones["features"]:
        props = feature["properties"]
        assert props.get("zone_name"), f"zone {props.get('location_id')} has no zone_name"
        assert props.get("borough"), f"zone {props.get('location_id')} has no borough"
        assert feature["geometry"]["type"] in ("Polygon", "MultiPolygon")
