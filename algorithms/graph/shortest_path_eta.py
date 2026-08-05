"""Dijkstra's shortest path from scratch (FR-4), used as a graph-path ETA
sanity check separate from the ML ETA model in models/.

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
from pathlib import Path

import duckdb
import networkx as nx

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"


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


def dijkstra(graph: nx.DiGraph, source: str, target: str) -> tuple[list[str], float]:
    """Return (path, total_weight) for the shortest path from source to
    target. Raises nx.NetworkXNoPath if unreachable (matches networkx's
    behavior so callers/tests can compare directly)."""
    if source not in graph or target not in graph:
        raise nx.NodeNotFound(f"source or target not in graph: {source!r}, {target!r}")

    dist = {source: 0.0}
    prev: dict[str, str] = {}
    visited: set[str] = set()
    heap = [(0.0, source)]

    while heap:
        d, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
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
    return path, dist[target]


def demo() -> None:
    graph = build_eta_graph()
    nodes = list(graph.nodes())
    source, target = nodes[0], nodes[len(nodes) // 2]

    my_path, my_eta = dijkstra(graph, source, target)
    ref_path = nx.dijkstra_path(graph, source, target, weight="weight")
    ref_eta = nx.dijkstra_path_length(graph, source, target, weight="weight")

    assert abs(my_eta - ref_eta) < 1e-6, f"eta mismatch: mine={my_eta}, networkx={ref_eta}"
    # path itself may differ if there are ties on total weight; weight match is
    # the real correctness bar (see tests/test_algorithms.py for the strict check).
    print(f"{source} -> {target}")
    print(f"  my path:  {my_path}  eta={my_eta:.1f} min")
    print(f"  nx path:  {ref_path}  eta={ref_eta:.1f} min")


if __name__ == "__main__":
    demo()
