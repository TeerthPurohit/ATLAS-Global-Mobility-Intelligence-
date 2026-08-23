# Roadmap

Layers, not sprints — mirrors `project_plan.md`. Update the checkboxes as
layers complete; this is the single "how far along are we" view alongside
`.claude/memory.md` (memory.md is the detailed *state*, this is the
checklist *progress*).

- [x] **Layer 0 — Data Foundation.** HVFHV trip rows loaded into DuckDB
      (`scripts/load_raw_to_duckdb.py`) -- 113M+ rows.
- [x] **Layer 1 — dbt Transformation.** Staging/intermediate/marts built and
      tested: `zone_hourly_demand`, `zone_fare_stats`, `zone_pair_flows`,
      `canonical_areas`.
- [x] **Layer 2 — Algorithms.** Spatial (KD-tree, geohash), graph (PageRank,
      Dijkstra), time-series (EWMA, seasonal decomposition) — implemented
      from scratch and validated against reference libraries.
- [x] **Layer 3 — Model Ladder.** Demand ladder (linear, EWMA baseline,
      XGBoost, LSTM) and fare model (XGBoost) all trained, evaluated on
      chronological splits, and compared — see
      `models/evaluation/metrics_report.md`.
- [x] **Layer 4 — Hybrid RAG.** Insight generation, embeddings, NL-to-SQL
      with a QueryPlan compiler, router, reranking, and a semantic cache.
      NYC is `full_rag` -- real SQL plus vector-retrieval synthesis.
- [x] **Layer 5 — Serving & Presentation.** FastAPI backend (city, journey,
      prediction, mobility, context, analytics routers) and the Next.js
      `frontend-web` app with an NYC zone-map hero.

**Scope note (2026-08-23):** the 519-city global layer that briefly sat on
top of Layer 5 was removed ([ADR-011](../adr/ADR-011-retreat-from-global-coverage.md)),
and London followed ([ADR-012](../adr/ADR-012-nyc-only.md)). Coverage is NYC
only; a city is added only with its own real trip corpus.

## Sequencing constraint

Strictly top to bottom — Layer 2 needs Layer 1's marts, Layer 3 needs
Layer 2's algorithm outputs as features, Layer 4 needs Layer 3's model
outputs, Layer 5 needs everything. Don't start a layer's spec work believing
it can run ahead of its dependency.

## Timeline

The original guide was roughly 2 weeks per layer at ~12hrs/week, 9 weeks
total. All six layers are now done; `project_plan.md` is historical record
rather than a live schedule. Let the spec acceptance criteria, not the
calendar, decide when work is done.
