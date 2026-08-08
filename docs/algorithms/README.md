# Algorithms

From-scratch implementations, each validated against a reference library
(standards.md's "prove your implementation is correct" bar) and each
operating on generic arrays/points/graphs internally -- NYC-specific naming
(zone ids, `nyc_rides.duckdb`) shows up only in default file paths, CLI
demo sections, and docstrings, not in the algorithm logic itself
(SPEC-013 FR-12).

## Spatial -- `algorithms/spatial/`

- **`kdtree_zone_lookup.py`**: 2D KD-tree (recursive median split, alternating
  lat/lon axis) over `ZonePoint(location_id, zone, lat, lon)`. Validated
  against a linear scan on the same query set (`benchmark_summary()` asserts
  identical results). Real measured benchmark
  (`algorithms/spatial/output/kdtree_benchmark.json`, regenerate via
  `scripts/generate_algorithm_artifacts.py`): 263 zones, tree depth 9, **5.72x
  speedup** over linear scan across 2000 random queries.
- **`geohash_grid.py`**: geohash-based coarse spatial indexing/bucketing.

## Graph -- `algorithms/graph/`

- **`build_zone_graph.py`**: builds a weighted directed zone-pair graph from
  `zone_pair_flows`.
- **`pagerank_hubs.py`**: from-scratch power-iteration PageRank (damping
  0.85), validated against `networkx.pagerank` on the same graph. Real
  output (`algorithms/graph/output/pagerank_hubs.json`): 261 zones, 55,459
  edges; top hub is "Outside of NYC" (0.038 score), then JFK Airport (0.019) --
  matches the intuitive network-flow story (trips terminating outside the
  zone system, plus the airport, dominate weighted degree).
- **`shortest_path_eta.py`**: Dijkstra shortest path over the same zone
  graph, validated against `networkx.dijkstra_path`.

## Time series -- `algorithms/timeseries/`

- **`ewma_smoothing.py`**: exponentially-weighted moving average, validated
  against `pandas.ewm`. Backs `model_service.py`'s honest fallback when the
  XGBoost demand model extrapolates negative for a low-volume zone
  (`ewma_fallback_v1`).
- **`seasonality_decompose.py`**: additive seasonal decomposition over
  hourly zone demand (see `algorithms/timeseries/output/*_decomp.png` for
  real per-zone decomposition plots).

## Why from-scratch, not a library call

Interview-legible engineering: the value of this repo is being able to
explain *how* KD-tree/PageRank/Dijkstra/EWMA work, not just call
`scipy`/`networkx`/`pandas`. Every implementation is still checked against
the reference library so "from scratch" doesn't mean "unverified" (rule 0).
