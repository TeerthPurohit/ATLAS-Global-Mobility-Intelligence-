"""Geohash encoding of zone centroids + prefix-matching for "nearby zones."

Geohash interleaves alternating lat/lon bisections into a base32 string;
zones sharing a prefix occupy the same (or an adjacent) grid cell. This is a
cheap, index-friendly stand-in for true nearest-neighbor (see
kdtree_zone_lookup.py for the exact version) — the documented limitation is
that a query point near a cell edge can have its true nearest neighbor in a
sibling cell that shares almost none of the prefix (edge effect), because
geohash grid cells are axis-aligned boxes, not distance-based regions.

Uses the `geohash2` package already in requirements.txt rather than
reimplementing base32 interleaving by hand — that library call itself
*is* the "known building block," the from-scratch algorithm work for this
spec lives in the KD-tree.
"""
from __future__ import annotations

from pathlib import Path

import geohash2
import pandas as pd

CENTROIDS_PATH = Path(__file__).resolve().parents[2] / "data" / "lookup" / "zone_centroids.csv"


def load_zone_geohashes(precision: int = 6, path: Path = CENTROIDS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["geohash"] = df.apply(
        lambda r: geohash2.encode(r.latitude, r.longitude, precision=precision), axis=1
    )
    return df


def nearby_zones(df: pd.DataFrame, location_id: int, prefix_len: int = 5) -> pd.DataFrame:
    """Zones sharing a geohash prefix of length `prefix_len` with `location_id`."""
    row = df.loc[df.LocationID == location_id]
    if row.empty:
        raise ValueError(f"unknown LocationID {location_id}")
    prefix = row.iloc[0].geohash[:prefix_len]
    return df[df.geohash.str.startswith(prefix) & (df.LocationID != location_id)]


if __name__ == "__main__":
    zones = load_zone_geohashes(precision=7)
    print(zones[["LocationID", "zone", "borough", "latitude", "longitude", "geohash"]].head(10))

    # demo: zones near Times Square (LocationID 230 in the TLC lookup)
    target_id = 230
    target = zones.loc[zones.LocationID == target_id].iloc[0]
    print(f"\ntarget zone: {target.zone} ({target.borough}), geohash={target.geohash}")

    for plen in (4, 5, 6):
        matches = nearby_zones(zones, target_id, prefix_len=plen)
        print(f"prefix_len={plen}: {len(matches)} zones share prefix '{target.geohash[:plen]}'")
        print(matches[["zone", "borough", "geohash"]].to_string(index=False))

    print(
        "\nlimitation: prefix matching is a grid-box heuristic, not a distance query — "
        "a zone centroid just across a geohash cell boundary from the target can be "
        "closer in real distance than a zone sharing a long prefix but sitting near the "
        "far edge of the same cell. Use kdtree_zone_lookup.py when true nearest-neighbor "
        "distance matters."
    )
