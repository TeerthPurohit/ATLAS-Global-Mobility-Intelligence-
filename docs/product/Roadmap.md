# Roadmap

Layers, not sprints — mirrors `project_plan.md`. Update the checkboxes as
layers complete; this is the single "how far along are we" view alongside
`.claude/memory.md` (memory.md is the detailed *state*, this is the
checklist *progress*).

- [x] **Layer 0 — Data Foundation.** 8-10M HVFHV rows loaded into DuckDB.
- [ ] **Layer 1 — dbt Transformation.** Staging/intermediate/marts written,
      `dbt test` not yet confirmed clean (in progress as of 2026-08-05).
- [ ] **Layer 2 — Algorithms.** Spatial (KD-tree, geohash), graph (PageRank,
      Dijkstra), time-series (EWMA, decomposition) — all stubbed, none
      implemented.
- [x] **Layer 3 — Model Ladder.** Demand ladder (linear, EWMA baseline,
      XGBoost, LSTM) and fare model (XGBoost) all trained, evaluated on
      chronological splits, and compared — see
      `models/evaluation/metrics_report.md`.
- [ ] **Layer 4 — Hybrid RAG.** Insight generation, embeddings, NL-to-SQL,
      router — all stubbed.
- [ ] **Layer 5 — Serving & Presentation.** FastAPI backend, React frontend,
      deployment — file scaffolding exists, no implementation.

## Sequencing constraint

Strictly top to bottom — Layer 2 needs Layer 1's marts, Layer 3 needs
Layer 2's algorithm outputs as features, Layer 4 needs Layer 3's model
outputs, Layer 5 needs everything. Don't start a layer's spec work believing
it can run ahead of its dependency.

## Timeline

Guide, not contract, per `project_plan.md`'s closing notes: roughly 2 weeks
per layer at ~12hrs/week, 9 weeks total. Let the spec acceptance criteria,
not the calendar, decide when a layer is done.
