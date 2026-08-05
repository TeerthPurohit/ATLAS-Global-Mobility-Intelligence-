"""Correctness tests: from-scratch algorithms vs. reference libraries.

Per standards.md, every from-scratch algorithm gets one test comparing its
output to the reference library on the same input. This module covers:
- SPEC-003 (spatial): kdtree_zone_lookup.py vs scipy.spatial.KDTree.
- SPEC-004 (graph): pagerank_hubs.py vs networkx.pagerank,
  shortest_path_eta.py vs networkx.dijkstra_path.
- SPEC-005 (timeseries): ewma_smoothing.py vs pandas.ewm,
  seasonality_decompose.py vs statsmodels.tsa.seasonal.MSTL.
"""
import random
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pytest
from scipy.spatial import KDTree as ScipyKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms.spatial.kdtree_zone_lookup import KDTree, load_zone_points
from algorithms.graph.build_zone_graph import build_zone_graph
from algorithms.graph.pagerank_hubs import pagerank, DAMPING
from algorithms.graph.shortest_path_eta import build_eta_graph, dijkstra
from algorithms.timeseries.ewma_smoothing import ewma
from algorithms.timeseries.seasonality_decompose import decompose

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse" / "nyc_rides.duckdb"
requires_warehouse = pytest.mark.skipif(not DB_PATH.exists(), reason="warehouse not built")


def test_kdtree_matches_scipy_nearest_neighbor():
    points = load_zone_points()
    tree = KDTree(points)

    scipy_tree = ScipyKDTree([(p.lat, p.lon) for p in points])

    random.seed(42)
    queries = [(random.uniform(40.49, 40.92), random.uniform(-74.26, -73.68)) for _ in range(500)]

    for lat, lon in queries:
        ours = tree.nearest(lat, lon)
        _, idx = scipy_tree.query((lat, lon))
        expected = points[idx]
        assert ours.location_id == expected.location_id, (
            f"query ({lat}, {lon}): got zone {ours.location_id}, scipy says {expected.location_id}"
        )


# ---- build_zone_graph ----

@requires_warehouse
def test_zone_graph_has_nodes_and_weighted_edges():
    graph = build_zone_graph()
    assert graph.number_of_nodes() > 0
    assert graph.number_of_edges() > 0
    assert all(d["weight"] > 0 for _, _, d in graph.edges(data=True))
    assert not any(u == v for u, v in graph.edges()), "self-loops should be excluded"


# ---- pagerank_hubs: from-scratch power iteration vs networkx.pagerank ----

@requires_warehouse
def test_pagerank_matches_networkx():
    # Both sides must converge to (near) the true fixed point to compare
    # meaningfully -- networkx's own default tol=1e-6/max_iter=100 stops
    # short of full convergence on this graph, which shows up as a spurious
    # "mismatch" against our tighter-converged output. Tighten both.
    graph = build_zone_graph()
    mine = pagerank(graph, epsilon=1e-12, max_iter=1000)
    reference = nx.pagerank(graph, alpha=DAMPING, weight="weight", tol=1e-12, max_iter=1000)

    assert set(mine) == set(reference)
    max_diff = max(abs(mine[n] - reference[n]) for n in graph.nodes())
    assert max_diff < 1e-6
    assert abs(sum(mine.values()) - 1.0) < 1e-6


def test_pagerank_matches_networkx_small_synthetic_graph():
    graph = nx.DiGraph()
    graph.add_weighted_edges_from(
        [
            ("A", "B", 2.0),
            ("B", "C", 1.0),
            ("C", "A", 1.0),
            ("C", "B", 1.0),
        ]
    )
    mine = pagerank(graph, epsilon=1e-12, max_iter=1000)
    reference = nx.pagerank(graph, alpha=DAMPING, weight="weight", tol=1e-12, max_iter=1000)
    for node in graph.nodes():
        assert mine[node] == pytest.approx(reference[node], abs=1e-9)


# ---- shortest_path_eta: from-scratch Dijkstra vs networkx.dijkstra_path ----

@requires_warehouse
def test_dijkstra_matches_networkx_on_zone_graph():
    graph = build_eta_graph()
    nodes = list(graph.nodes())
    source, target = nodes[0], nodes[len(nodes) // 2]

    _, my_eta = dijkstra(graph, source, target)
    ref_eta = nx.dijkstra_path_length(graph, source, target, weight="weight")
    assert my_eta == pytest.approx(ref_eta, abs=1e-6)


def test_dijkstra_matches_networkx_small_synthetic_graph():
    graph = nx.DiGraph()
    graph.add_weighted_edges_from(
        [
            ("A", "B", 4.0),
            ("A", "C", 1.0),
            ("C", "B", 1.0),
            ("B", "D", 1.0),
            ("C", "D", 5.0),
        ]
    )
    my_path, my_eta = dijkstra(graph, "A", "D")
    ref_path = nx.dijkstra_path(graph, "A", "D", weight="weight")
    ref_eta = nx.dijkstra_path_length(graph, "A", "D", weight="weight")

    assert my_path == ref_path
    assert my_eta == pytest.approx(ref_eta, abs=1e-9)


def test_dijkstra_no_path_raises_like_networkx():
    graph = nx.DiGraph()
    graph.add_weighted_edges_from([("A", "B", 1.0)])
    graph.add_node("C")
    with pytest.raises(nx.NetworkXNoPath):
        dijkstra(graph, "A", "C")
    with pytest.raises(nx.NetworkXNoPath):
        nx.dijkstra_path(graph, "A", "C")


# ---- ewma_smoothing: from-scratch recursive EWMA vs pandas.ewm ----

def test_ewma_matches_pandas_ewm():
    rng = np.random.default_rng(42)
    x = rng.poisson(lam=50, size=500).astype(float)

    for alpha in (0.1, 0.3, 0.7):
        ours = ewma(x, alpha)
        ref = pd.Series(x).ewm(alpha=alpha, adjust=False).mean().to_numpy()
        assert np.allclose(ours, ref, atol=1e-9)


# ---- seasonality_decompose: from-scratch trend/daily/weekly split vs MSTL ----

def test_decompose_matches_statsmodels_mstl():
    from statsmodels.tsa.seasonal import MSTL

    rng = np.random.default_rng(7)
    n = 24 * 28  # 4 weeks hourly, one continuous block -- no gap-crossing concern here
    t = np.arange(n)
    trend = 100 + 0.02 * t
    daily = 1 + 0.4 * np.sin(2 * np.pi * t / 24)
    weekly = 1 + 0.15 * np.sin(2 * np.pi * t / (24 * 7))
    noise = 1 + rng.normal(0, 0.03, n)
    y = trend * daily * weekly * noise

    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    series = pd.Series(y, index=idx)

    ours = decompose(series, model="multiplicative")

    ref = MSTL(series, periods=(24, 24 * 7)).fit()
    ref_seasonal = ref.seasonal.sum(axis=1).to_numpy()
    our_seasonal_log = np.log(ours.daily) + np.log(ours.weekly)

    # MSTL's seasonal components live on the raw (additive) scale of the
    # series, ours on the multiplicative log scale, so compare the shape of
    # the oscillation (correlation) rather than absolute values.
    valid = ~np.isnan(ours.trend)
    corr = np.corrcoef(our_seasonal_log[valid], ref_seasonal[valid])[0, 1]
    assert corr > 0.9

    # both are ~week-long centered moving averages of the same series
    trend_corr = np.corrcoef(ours.trend[valid], ref.trend.to_numpy()[valid])[0, 1]
    assert trend_corr > 0.95

    # reconstruction sanity: trend*daily*weekly*resid must equal the input
    reconstructed = ours.trend * ours.daily * ours.weekly * ours.resid
    assert np.allclose(reconstructed[valid], y[valid], rtol=1e-6)


if __name__ == "__main__":
    test_kdtree_matches_scipy_nearest_neighbor()
    print("OK: from-scratch KD-tree matches scipy.spatial.KDTree on 500 random queries")
