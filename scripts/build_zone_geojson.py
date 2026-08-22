"""Convert the NYC TLC taxi-zone shapefile into a simplified GeoJSON for the
map hero (ADR-011 phase 7).

One-time, offline. The repo already ships `data/raw/taxi_zones.zip` (the TLC's
own shapefile); this unpacks it, reprojects from NY State Plane (EPSG:2263) to
WGS84, simplifies the geometry, and writes `data/lookup/taxi_zones.geojson`.

Uses DuckDB's `spatial` extension rather than geopandas -- DuckDB is already a
hard dependency of this repo, and geopandas would pull in GDAL/PROJ/fiona for
a single one-time conversion.

    python scripts/build_zone_geojson.py
"""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
SHAPEFILE_ZIP = REPO_ROOT / "data" / "raw" / "taxi_zones.zip"
OUT_PATH = REPO_ROOT / "data" / "lookup" / "taxi_zones.geojson"

# Degrees. ~11 m at NYC's latitude -- visually identical at city zoom, and it
# takes the file from several MB down to something a page can ship inline.
SIMPLIFY_TOLERANCE = 0.0001


def main() -> None:
    if not SHAPEFILE_ZIP.exists():
        raise SystemExit(f"missing {SHAPEFILE_ZIP} -- download the TLC taxi zone shapefile first")

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(SHAPEFILE_ZIP) as z:
            z.extractall(tmp)
        shp = next(Path(tmp).rglob("*.shp"))

        con = duckdb.connect()
        con.execute("INSTALL spatial; LOAD spatial;")
        # COPY ... TO takes a literal path, not a bind parameter -- these two
        # paths are repo-internal (a tempdir and a constant), never user input.
        con.execute(
            f"""
            COPY (
                SELECT
                    LocationID AS location_id,
                    zone       AS zone_name,
                    borough,
                    ST_Simplify(
                        -- always_xy: EPSG:4326's formal axis order is (lat, lon);
                        -- GeoJSON requires (lon, lat). Without this every zone
                        -- lands in the Indian Ocean.
                        ST_Transform(geom, 'EPSG:2263', 'EPSG:4326', always_xy := true),
                        {SIMPLIFY_TOLERANCE}
                    ) AS geom
                FROM ST_Read('{shp.as_posix()}')
                ORDER BY LocationID
            ) TO '{OUT_PATH.as_posix()}' WITH (FORMAT GDAL, DRIVER 'GeoJSON')
            """
        )
        con.close()

    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({size_kb:,.0f} KB)")


if __name__ == "__main__":
    main()
