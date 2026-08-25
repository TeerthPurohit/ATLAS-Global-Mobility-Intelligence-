# SPEC-004: Graph Algorithms — PageRank + Dijkstra

Owner: solo builder · Status: done · Layer: 2 · Depends on: SPEC-002 (`zone_pair_flows`, `int_trips_enriched`)

## Business Goal

Model NYC zones as a weighted directed graph of trip flows; answer "which
zones are hubs" (PageRank) and "shortest path by typical travel time"
(Dijkstra) as graph-theory features and sanity-check signals.

## Functional Requirements

- FR-1: `build_zone_graph.py` — read `zone_pair_flows` mart, build a
  weighted directed graph with `networkx` as the data structure.
- FR-2: `pagerank_hubs.py` — implement PageRank from scratch via power
  iteration (damping 0.85, uniform initial rank, iterate to convergence
  epsilon).
- FR-3: Validate hand-rolled PageRank against `networkx.pagerank()` on the
  same graph.
- FR-4: `shortest_path_eta.py` — Dijkstra with edge weights = average trip
  duration between zone pairs (from `int_trips_enriched`), as an
  ETA-by-graph-path sanity-check separate from the ML ETA model.

## Proposed Design

PageRank formula: `PR(p) = (1-d)/N + d * Σ(PR(q)/L(q))` over in-neighbors
`q`, `L(q)` = out-degree of `q`. Dijkstra: min-priority-queue, relax edges,
`O((V+E) log V)` with a binary heap — valid because trip-duration weights
are always positive (Dijkstra requires non-negative weights; this is why it
applies here and wouldn't for a graph with negative edges).

## Testing

- PageRank output must match `networkx.pagerank()` within floating-point
  tolerance on the same graph.
- Dijkstra shortest paths must match `networkx.dijkstra_path()` on the same
  graph and source/target.

## Risks

`zone_pair_flows` may have sparse or zero-flow pairs (zone combinations
with very few trips) — decide explicitly whether to include low-count edges
or threshold them out, and document the choice; don't let an implicit
threshold silently shape PageRank results.

## Acceptance Criteria

- [ ] Graph built from `zone_pair_flows`.
- [ ] PageRank implementation matches networkx within tolerance.
- [ ] Dijkstra implementation matches networkx within tolerance.
- [ ] Degree-centrality vs PageRank comparison documented (what PageRank
      captures that raw degree count doesn't).
