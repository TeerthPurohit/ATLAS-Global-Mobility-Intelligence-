"""Build a weighted directed zone-to-zone trip-flow graph from the
`zone_pair_flows` mart, using networkx as the data structure (FR-1).

Edge weight = total trip count pickup_zone -> dropoff_zone, summed across all
dates in the mart (the mart is one row per pickup_date x zone pair).

Design decisions (see specs/004-graph-algorithms/spec.md "Risks"):
- Self-loops (pickup_zone == dropoff_zone) are dropped: they don't represent
  movement between zones and would inflate a zone's own out-degree/PageRank
  mass for no graph-theoretic reason.
- No minimum-trip-count threshold is applied. `zone_pair_flows` only contains
  observed (nonzero) pairs, and edge weight already encodes flow strength, so
  a low-count pair (e.g. 1 trip) just carries little weight in PageRank/
  Dijkstra rather than being silently dropped.
"""

from pathlib import Path

import duckdb
import networkx as nx

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"


def build_zone_graph(db_path: Path = DEFAULT_DB_PATH) -> nx.DiGraph:
    """Return a directed graph of zones with edge attribute `weight` =
    total trip count pickup_zone -> dropoff_zone."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(
            """
            select pickup_zone, dropoff_zone, sum(trip_count) as weight
            from zone_pair_flows
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


def demo() -> None:
    graph = build_zone_graph()
    assert graph.number_of_nodes() > 0, "graph must have nodes"
    assert graph.number_of_edges() > 0, "graph must have edges"
    assert all("weight" in d for _, _, d in graph.edges(data=True))
    print(f"zones (nodes): {graph.number_of_nodes()}")
    print(f"zone-pair edges: {graph.number_of_edges()}")
    print(f"total flow (sum of weights): {sum(d['weight'] for _, _, d in graph.edges(data=True)):.0f}")


if __name__ == "__main__":
    demo()
