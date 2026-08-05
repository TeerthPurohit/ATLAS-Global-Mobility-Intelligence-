# SPEC-003: Spatial Algorithms — KD-Tree + Geohash

Owner: solo builder · Status: not started · Layer: 2 · Depends on: SPEC-001 (zone centroids)

## Business Goal

Given a lat/lon, find the nearest taxi zone in better than linear time —
and demonstrate a from-scratch understanding of space-partitioning, not
just a library call.

## Functional Requirements

- FR-1: `kdtree_zone_lookup.py` — build a KD-tree from scratch over the
  ~260 NYC TLC zone centroids (recursive median-split, alternating axis).
- FR-2: Nearest-neighbor query: given (lat, lon), return nearest zone.
- FR-3: Benchmark linear scan O(n) vs KD-tree O(log n) over repeated
  queries, with real timing numbers (not estimated — rule 2 in
  `.claude/rules.md`).
- FR-4: `geohash_grid.py` — encode zone centroids to geohash strings,
  demonstrate prefix-matching for "nearby zones."

## Proposed Design

Construction: recursively partition by alternating lat/lon at the median,
O(n log n) build. Query: traverse pruning branches whose bounding region
can't contain a closer point than current best; average O(log n), worst
case O(n) for degenerate trees (relevant here since NYC zone centroids
aren't uniformly distributed — Manhattan is dense, outer boroughs sparse).

## Testing

Compare from-scratch KD-tree nearest-neighbor output against
`scipy.spatial.KDTree` on the same zone centroid set and the same query
points — must match exactly (nearest zone is deterministic, no floating
tolerance needed for a discrete "which zone" answer).

## Risks

Zone centroids are unevenly distributed (dense Manhattan, sparse outer
boroughs) — a naive median-split tree can degrade toward linear on the
sparse side. Note actual observed depth/balance in the benchmark output,
don't assume balance.

## Acceptance Criteria

- [ ] KD-tree built and passes correctness test against scipy.
- [ ] Benchmark shows and reports real O(n) vs O(log n) timing difference.
- [ ] Geohash prefix-matching demonstrated with a documented limitation
      (edge effects at boundaries).
