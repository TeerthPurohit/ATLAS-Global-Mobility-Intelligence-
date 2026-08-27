"""Dijkstra's shortest path from scratch (FR-4), used as a graph-path ETA
sanity check separate from the ML ETA model in models/. Also A*, using a
haversine-distance heuristic over real zone centroids -- same graph, same
correctness bar (validated against networkx), compared to Dijkstra on nodes
expanded rather than wall-clock (see benchmark_astar_vs_dijkstra).

Edge weight = average trip duration (minutes) between zone pairs, computed
directly from `int_trips_enriched` (not the pre-aggregated zone_pair_flows
mart, per spec FR-4). Weights are always >= 0 (durations can't be negative),
which is exactly the precondition Dijkstra requires — it does not handle
negative edge weights correctly (Bellman-Ford would be needed for that).

Binary heap (heapq) is used as the min-priority-queue, giving the standard
O((V+E) log V) complexity.
"""

from __future__ import annotations

import heapq
import math
from pathlib import Path

import duckdb
import networkx as nx

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"

# Upper bound on travel speed for the A* heuristic below. Must never be
# exceeded by dist(u, target)/duration(u, target) for any real edge, or the
# heuristic overestimates cost and A* is no longer guaranteed optimal.
# Measured directly against every edge in build_eta_graph() (63,060 edges
# with known centroids): median implied speed 22.7 km/h, 99.99th percentile
# 57.9 km/h, true max 109.6 km/h (Great Kills Park -> Pelham Bay, a
# thin-sample outlier). 120 clears that measured max with margin rather than
# assuming a round-number highway speed.
MAX_SPEED_KMH = 120.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in km."""
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_eta_graph(db_path: Path = DEFAULT_DB_PATH) -> nx.DiGraph:
    """Directed graph of zones with edge attribute `weight` = average trip
    duration in minutes, pickup_zone -> dropoff_zone."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(
            """
            select pickup_zone, dropoff_zone, avg(trip_duration_minutes) as weight
            from int_trips_enriched
            where pickup_zone != dropoff_zone
            group by 1, 2
            """
        ).fetchdf()
    finally:
        con.close()

    graph = nx.DiGraph()
    for row in df.itertuples(index=False):
        graph.add_edge(row.pickup_zone, row.dropoff_zone, weight=float(row.weight))
    return graph


def load_zone_coords(db_path: Path = DEFAULT_DB_PATH) -> dict[str, tuple[float, float]]:
    """zone name -> (lat, lon) from the canonical_areas mart, keyed to match
    build_eta_graph()'s nodes (zone names, not location_id). Two names map
    to more than one location_id (`Corona`; `Governor's Island/Ellis
    Island/Liberty Island`) -- averaged, since the eta graph already
    collapses them into one node. Zones with no real centroid (`N/A`,
    `Outside of NYC`) are omitted, not fabricated."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(
            """
            select name, avg(latitude) as latitude, avg(longitude) as longitude
            from canonical_areas
            where latitude is not null and longitude is not null
            group by name
            """
        ).fetchdf()
    finally:
        con.close()
    return {row.name: (row.latitude, row.longitude) for row in df.itertuples(index=False)}


def dijkstra(graph: nx.DiGraph, source: str, target: str) -> tuple[list[str], float, int]:
    """Return (path, total_weight, nodes_expanded) for the shortest path
    from source to target. Raises nx.NetworkXNoPath if unreachable (matches
    networkx's behavior so callers/tests can compare directly). nodes_expanded
    is tracked so astar() below can be benchmarked against this on an equal
    footing (see benchmark_astar_vs_dijkstra)."""
    if source not in graph or target not in graph:
        raise nx.NodeNotFound(f"source or target not in graph: {source!r}, {target!r}")

    dist = {source: 0.0}
    prev: dict[str, str] = {}
    visited: set[str] = set()
    heap = [(0.0, source)]
    nodes_expanded = 0

    while heap:
        d, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        nodes_expanded += 1
        if node == target:
            break
        for _, neighbor, data in graph.out_edges(node, data=True):
            if neighbor in visited:
                continue
            new_dist = d + data["weight"]
            if new_dist < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_dist
                prev[neighbor] = node
                heapq.heappush(heap, (new_dist, neighbor))

    if target not in dist:
        raise nx.NetworkXNoPath(f"no path from {source!r} to {target!r}")

    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()
    return path, dist[target], nodes_expanded


def astar(
    graph: nx.DiGraph,
    source: str,
    target: str,
    coords: dict[str, tuple[float, float]],
) -> tuple[list[str], float, int]:
    """Same contract as dijkstra() -- (path, total_weight, nodes_expanded),
    same nx.NodeNotFound/nx.NetworkXNoPath behavior -- but guided by
    haversine(node, target)/MAX_SPEED_KMH as an admissible heuristic. A node
    missing from `coords` (no real centroid) gets h=0, which stays
    admissible, just uninformative for that node."""
    if source not in graph or target not in graph:
        raise nx.NodeNotFound(f"source or target not in graph: {source!r}, {target!r}")

    def h(node: str) -> float:
        if node not in coords or target not in coords:
            return 0.0
        lat1, lon1 = coords[node]
        lat2, lon2 = coords[target]
        return haversine_km(lat1, lon1, lat2, lon2) / MAX_SPEED_KMH * 60.0

    dist = {source: 0.0}
    prev: dict[str, str] = {}
    visited: set[str] = set()
    heap = [(h(source), source)]
    nodes_expanded = 0

    while heap:
        _, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        nodes_expanded += 1
        if node == target:
            break
        for _, neighbor, data in graph.out_edges(node, data=True):
            if neighbor in visited:
                continue
            new_dist = dist[node] + data["weight"]
            if new_dist < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_dist
                prev[neighbor] = node
                heapq.heappush(heap, (new_dist + h(neighbor), neighbor))

    if target not in dist:
        raise nx.NetworkXNoPath(f"no path from {source!r} to {target!r}")

    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()
    return path, dist[target], nodes_expanded


def benchmark_astar_vs_dijkstra(
    graph: nx.DiGraph,
    coords: dict[str, tuple[float, float]],
    sample_pairs: list[tuple[str, str]],
) -> dict:
    """Real measured comparison, same convention as
    algorithms/spatial/output/kdtree_benchmark.json: nodes expanded, not
    wall-clock -- at 262 nodes wall-clock differences are noise, and this
    repo's measured-numbers discipline means only a real, demoable number
    gets reported. Asserts astar and dijkstra agree on cost for every
    reachable pair, as an extra correctness check beyond the networkx
    comparison in tests/test_algorithms.py."""
    astar_expanded, dijkstra_expanded = [], []
    unreachable = 0

    for source, target in sample_pairs:
        try:
            _, a_cost, a_exp = astar(graph, source, target, coords)
            _, d_cost, d_exp = dijkstra(graph, source, target)
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            unreachable += 1
            continue
        assert abs(a_cost - d_cost) < 1e-6, (
            f"cost mismatch {source!r} -> {target!r}: astar={a_cost}, dijkstra={d_cost}"
        )
        astar_expanded.append(a_exp)
        dijkstra_expanded.append(d_exp)

    avg_astar = sum(astar_expanded) / len(astar_expanded) if astar_expanded else 0.0
    avg_dijkstra = sum(dijkstra_expanded) / len(dijkstra_expanded) if dijkstra_expanded else 0.0
    reduction_pct = (1 - avg_astar / avg_dijkstra) * 100 if avg_dijkstra else 0.0

    return {
        "n_zones": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "n_sample_pairs": len(sample_pairs),
        "n_unreachable": unreachable,
        "max_speed_kmh": MAX_SPEED_KMH,
        "avg_nodes_expanded_astar": round(avg_astar, 2),
        "avg_nodes_expanded_dijkstra": round(avg_dijkstra, 2),
        "reduction_pct": round(reduction_pct, 1),
        "note": (
            "nodes-expanded is the honest metric at this graph size; "
            "wall-clock difference between astar and dijkstra here is within "
            "measurement noise, unlike kdtree_benchmark.json where wall-clock "
            "is the right metric at a much larger n."
        ),
    }


def demo() -> None:
    import random

    graph = build_eta_graph()
    coords = load_zone_coords()
    nodes = list(graph.nodes())
    source, target = nodes[0], nodes[len(nodes) // 2]

    my_path, my_eta, my_expanded = dijkstra(graph, source, target)
    ref_path = nx.dijkstra_path(graph, source, target, weight="weight")
    ref_eta = nx.dijkstra_path_length(graph, source, target, weight="weight")

    assert abs(my_eta - ref_eta) < 1e-6, f"eta mismatch: mine={my_eta}, networkx={ref_eta}"
    # path itself may differ if there are ties on total weight; weight match is
    # the real correctness bar (see tests/test_algorithms.py for the strict check).
    print(f"{source} -> {target}")
    print(f"  dijkstra path:  {my_path}  eta={my_eta:.1f} min  nodes_expanded={my_expanded}")
    print(f"  nx path:        {ref_path}  eta={ref_eta:.1f} min")

    a_path, a_eta, a_expanded = astar(graph, source, target, coords)
    assert abs(a_eta - my_eta) < 1e-6, f"astar/dijkstra eta mismatch: astar={a_eta}, dijkstra={my_eta}"
    print(f"  astar path:     {a_path}  eta={a_eta:.1f} min  nodes_expanded={a_expanded}")

    random.seed(42)
    coord_nodes = [n for n in nodes if n in coords]
    sample_pairs = [(random.choice(coord_nodes), random.choice(coord_nodes)) for _ in range(100)]
    result = benchmark_astar_vs_dijkstra(graph, coords, sample_pairs)
    print(f"  benchmark (n={result['n_sample_pairs']} pairs): "
          f"astar avg nodes expanded={result['avg_nodes_expanded_astar']}, "
          f"dijkstra avg nodes expanded={result['avg_nodes_expanded_dijkstra']}, "
          f"reduction={result['reduction_pct']}%")


if __name__ == "__main__":
    demo()
