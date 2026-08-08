"""PageRank from scratch via power iteration (FR-2).

PR(p) = (1-d)/N + d * sum(PR(q)/L(q) for q in in-neighbors(p))
where L(q) = out-degree (weighted, by trip-flow edge weight) of q.

Weighted variant: a q's "vote" for p is split across q's out-edges in
proportion to edge weight, not split evenly — L(q) is q's total out-weight,
and PR(q)/L(q) is scaled by weight(q, p). This matches networkx's
weighted pagerank so the correctness test is meaningful (unweighted
power iteration on a flow graph would just be wrong).

PageRank vs. raw weighted degree (measured via demo(), see run log): both
rank "Outside of NYC" and the two airports at the top -- unsurprising, they
have the largest raw trip volume. But below that they diverge:
Times Sq/Theatre District, Midtown Center, and West Chelsea/Hudson Yards are
top-10 by raw degree yet fall out of the PageRank top 10, while Crown
Heights North, Bushwick South, Park Slope, and East New York rank *higher*
in PageRank than their raw trip volume alone would predict. That's the
recursive part of PageRank showing up: those Brooklyn/Queens zones receive a
disproportionate share of their inbound trips from other already-important
zones, not just from a large number of low-importance ones, whereas
Midtown's volume is spread more broadly across many lower-rank origins.
Raw degree only sees trip counts; PageRank sees who those trips come from.
"""

from __future__ import annotations

import networkx as nx

DAMPING = 0.85
EPSILON = 1e-12
MAX_ITER = 1000


def pagerank(graph: nx.DiGraph, damping: float = DAMPING, epsilon: float = EPSILON, max_iter: int = MAX_ITER) -> dict[str, float]:
    nodes = list(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {}

    rank = {node: 1.0 / n for node in nodes}
    out_weight = {node: sum(d["weight"] for _, _, d in graph.out_edges(node, data=True)) for node in nodes}
    in_edges = {node: list(graph.in_edges(node, data=True)) for node in nodes}
    dangling = [node for node in nodes if out_weight[node] == 0]

    for _ in range(max_iter):
        dangling_mass = sum(rank[node] for node in dangling) / n if dangling else 0.0
        new_rank = {}
        for node in nodes:
            incoming = 0.0
            for q, _, d in in_edges[node]:
                incoming += rank[q] * d["weight"] / out_weight[q]
            new_rank[node] = (1 - damping) / n + damping * (incoming + dangling_mass)

        diff = sum(abs(new_rank[node] - rank[node]) for node in nodes)
        rank = new_rank
        if diff < epsilon:
            break

    return rank


def top_hubs(graph: nx.DiGraph, k: int = 10) -> list[tuple[str, float]]:
    rank = pagerank(graph)
    return sorted(rank.items(), key=lambda kv: kv[1], reverse=True)[:k]


def hub_summary(graph: nx.DiGraph, k: int = 10) -> dict:
    """Top-k hubs with rank/score/raw-degree, for persisting as a real
    artifact instead of a hand-typed list in the UI."""
    rank = pagerank(graph)
    degree = dict(graph.degree(weight="weight"))
    ranked = sorted(rank.items(), key=lambda kv: kv[1], reverse=True)[:k]
    return {
        "damping": DAMPING,
        "n_zones": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "top_hubs": [
            {
                "rank": i + 1,
                "zone": zone,
                "pagerank_score": score,
                "raw_weighted_degree": degree.get(zone, 0.0),
            }
            for i, (zone, score) in enumerate(ranked)
        ],
    }


def demo() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_zone_graph import build_zone_graph

    graph = build_zone_graph()
    mine = pagerank(graph)
    reference = nx.pagerank(graph, alpha=DAMPING, weight="weight", tol=1e-12, max_iter=1000)

    max_diff = max(abs(mine[node] - reference[node]) for node in graph.nodes())
    assert max_diff < 1e-6, f"pagerank mismatch vs networkx: max diff {max_diff}"
    assert abs(sum(mine.values()) - 1.0) < 1e-6, "pagerank must sum to ~1"

    print(f"max abs diff vs networkx.pagerank: {max_diff:.2e}")
    print("top 10 hub zones by PageRank:")
    for zone, score in top_hubs(graph, 10):
        print(f"  {zone}: {score:.5f}")

    degree = dict(graph.degree(weight="weight"))
    print("top 10 zones by raw weighted degree (for comparison):")
    for zone, _ in sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:10]:
        print(f"  {zone}: degree={degree[zone]:.0f}, pagerank={mine[zone]:.5f}")


if __name__ == "__main__":
    demo()
