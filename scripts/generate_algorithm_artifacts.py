"""Persist real measured output for algorithms/ so the Algorithms page can
read actual artifacts instead of hand-typed numbers. Run after any change to
zone_pair_flows or zone_centroids.csv:

    python scripts/generate_algorithm_artifacts.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from algorithms.graph.build_zone_graph import build_zone_graph  # noqa: E402
from algorithms.graph.pagerank_hubs import hub_summary  # noqa: E402
from algorithms.graph.shortest_path_eta import (  # noqa: E402
    benchmark_astar_vs_dijkstra,
    build_eta_graph,
    load_zone_coords,
)
from algorithms.spatial.kdtree_zone_lookup import (  # noqa: E402
    benchmark_summary,
    load_zone_points,
)

KDTREE_OUT = REPO_ROOT / "algorithms" / "spatial" / "output" / "kdtree_benchmark.json"
PAGERANK_OUT = REPO_ROOT / "algorithms" / "graph" / "output" / "pagerank_hubs.json"
ASTAR_OUT = REPO_ROOT / "algorithms" / "graph" / "output" / "astar_benchmark.json"


def main() -> None:
    KDTREE_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAGERANK_OUT.parent.mkdir(parents=True, exist_ok=True)
    ASTAR_OUT.parent.mkdir(parents=True, exist_ok=True)

    kdtree_result = benchmark_summary(load_zone_points())
    KDTREE_OUT.write_text(json.dumps(kdtree_result, indent=2))
    print(f"wrote {KDTREE_OUT} (speedup={kdtree_result['speedup_x']:.2f}x)")

    graph = build_zone_graph()
    pagerank_result = hub_summary(graph)
    PAGERANK_OUT.write_text(json.dumps(pagerank_result, indent=2))
    print(f"wrote {PAGERANK_OUT} (top hub={pagerank_result['top_hubs'][0]['zone']})")

    eta_graph = build_eta_graph()
    coords = load_zone_coords()
    coord_nodes = [n for n in eta_graph.nodes() if n in coords]
    random.seed(42)
    sample_pairs = [(random.choice(coord_nodes), random.choice(coord_nodes)) for _ in range(200)]
    astar_result = benchmark_astar_vs_dijkstra(eta_graph, coords, sample_pairs)
    ASTAR_OUT.write_text(json.dumps(astar_result, indent=2))
    print(f"wrote {ASTAR_OUT} (nodes-expanded reduction={astar_result['reduction_pct']}%)")


if __name__ == "__main__":
    main()
