"""From-scratch KD-tree over NYC TLC zone centroids for nearest-neighbor lookup.

Centroids source: data/lookup/zone_centroids.csv, derived from the official
NYC TLC taxi_zones shapefile (EPSG:2263 -> EPSG:4326 centroid via DuckDB's
spatial extension). See that file's header for provenance.

Construction: recursive median-split, alternating lat/lon axis, O(n log n).
Query: branch-and-bound nearest neighbor, pruning subtrees whose splitting
plane is farther than the current best distance. Average O(log n); the
docstring in the class notes the degenerate-tree risk from uneven zone
density (dense Manhattan vs sparse outer boroughs) per SPEC-003 risks.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CENTROIDS_PATH = Path(__file__).resolve().parents[2] / "data" / "lookup" / "zone_centroids.csv"


@dataclass
class ZonePoint:
    location_id: int
    zone: str
    lat: float
    lon: float


class KDNode:
    __slots__ = ("point", "axis", "left", "right")

    def __init__(self, point: ZonePoint, axis: int, left: "KDNode | None", right: "KDNode | None"):
        self.point = point
        self.axis = axis
        self.left = left
        self.right = right


def _coord(point: ZonePoint, axis: int) -> float:
    return point.lat if axis == 0 else point.lon


def _sq_dist(a_lat: float, a_lon: float, point: ZonePoint) -> float:
    return (a_lat - point.lat) ** 2 + (a_lon - point.lon) ** 2


class KDTree:
    """2D KD-tree (axes: 0=lat, 1=lon), built by recursive median split."""

    def __init__(self, points: list[ZonePoint]):
        self.root = self._build(list(points), depth=0)

    def _build(self, points: list[ZonePoint], depth: int) -> KDNode | None:
        if not points:
            return None
        axis = depth % 2
        points.sort(key=lambda p: _coord(p, axis))
        mid = len(points) // 2
        median_point = points[mid]
        left = self._build(points[:mid], depth + 1)
        right = self._build(points[mid + 1 :], depth + 1)
        return KDNode(median_point, axis, left, right)

    def nearest(self, lat: float, lon: float) -> ZonePoint:
        best: list = [None, float("inf")]  # [point, sq_dist]

        def visit(node: KDNode | None):
            if node is None:
                return
            d = _sq_dist(lat, lon, node.point)
            if d < best[1]:
                best[0], best[1] = node.point, d

            axis_val = lat if node.axis == 0 else lon
            node_val = _coord(node.point, node.axis)
            diff = axis_val - node_val

            near, far = (node.left, node.right) if diff < 0 else (node.right, node.left)
            visit(near)
            # only descend into far side if it could contain a closer point
            if diff * diff < best[1]:
                visit(far)

        visit(self.root)
        return best[0]

    def depth(self) -> int:
        def _d(node: KDNode | None) -> int:
            if node is None:
                return 0
            return 1 + max(_d(node.left), _d(node.right))

        return _d(self.root)


def load_zone_points(path: Path = CENTROIDS_PATH) -> list[ZonePoint]:
    df = pd.read_csv(path)
    return [
        ZonePoint(int(r.LocationID), r.zone, float(r.latitude), float(r.longitude))
        for r in df.itertuples()
    ]


def linear_nearest(points: list[ZonePoint], lat: float, lon: float) -> ZonePoint:
    return min(points, key=lambda p: _sq_dist(lat, lon, p))


def benchmark_summary(points: list[ZonePoint], n_queries: int = 2000) -> dict:
    """Run the linear-scan-vs-KD-tree benchmark and return measured results
    (used both by the CLI printout and by scripts/generate_algorithm_artifacts.py
    to persist a real artifact instead of a hand-typed number in the UI)."""
    import random

    random.seed(0)
    # NYC bounding box, roughly
    queries = [(random.uniform(40.49, 40.92), random.uniform(-74.26, -73.68)) for _ in range(n_queries)]

    tree = KDTree(points)

    t0 = time.perf_counter()
    linear_results = [linear_nearest(points, lat, lon).location_id for lat, lon in queries]
    t_linear = time.perf_counter() - t0

    t0 = time.perf_counter()
    tree_results = [tree.nearest(lat, lon).location_id for lat, lon in queries]
    t_tree = time.perf_counter() - t0

    assert linear_results == tree_results, "KD-tree and linear scan disagree"

    return {
        "n_zones": len(points),
        "tree_depth": tree.depth(),
        "n_queries": n_queries,
        "linear_scan_seconds": t_linear,
        "linear_scan_us_per_query": t_linear / n_queries * 1e6,
        "kdtree_seconds": t_tree,
        "kdtree_us_per_query": t_tree / n_queries * 1e6,
        "speedup_x": t_linear / t_tree,
    }


def _benchmark(points: list[ZonePoint], n_queries: int = 2000) -> None:
    summary = benchmark_summary(points, n_queries)
    print(f"n zones = {summary['n_zones']}, tree depth = {summary['tree_depth']} (balanced depth ~= {len(points).bit_length()})")
    print(f"{n_queries} queries, linear scan: {summary['linear_scan_seconds']:.4f}s ({summary['linear_scan_us_per_query']:.2f} us/query)")
    print(f"{n_queries} queries, KD-tree:     {summary['kdtree_seconds']:.4f}s ({summary['kdtree_us_per_query']:.2f} us/query)")
    print(f"speedup: {summary['speedup_x']:.2f}x")


if __name__ == "__main__":
    zone_points = load_zone_points()
    _benchmark(zone_points)
