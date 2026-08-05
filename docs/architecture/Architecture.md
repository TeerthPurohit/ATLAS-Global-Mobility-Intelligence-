# Architecture

Full detail version of `.claude/architecture.md` — read that first for the
compressed version an agent needs; this expands each layer with the
actual technology choices and why.

## System diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 0: Data Foundation                                        │
│  TLC HVFHV parquet (raw) ──read_parquet()──> DuckDB raw table   │
└───────────────────────────────┬───────────────────────────────-─┘
                                 │
┌────────────────────────────────▼──────────────────────────────-─┐
│ Layer 1: dbt (staging → intermediate → marts)                   │
│  stg_trips, stg_zones → int_trips_enriched →                    │
│  zone_hourly_demand | zone_fare_stats | zone_pair_flows         │
└──────────┬──────────────────────────────────────────┬──────────┘
           │                                          │
┌──────────▼─────────────────┐          ┌─────────────▼───────────┐
│ Layer 2: Algorithms         │          │ Layer 3: Model Ladder   │
│  KD-tree, geohash           │─features►│  linear→ewma→xgb→lstm   │
│  PageRank, Dijkstra         │          │  + fare model            │
│  EWMA, seasonal decompose   │          │  + evaluation report     │
└──────────┬──────────────────┘          └─────────────┬───────────┘
           │                                            │
           └───────────────────┬────────────────────────┘
                                ▼
                  ┌─────────────────────────────┐
                  │ Layer 4: Hybrid RAG          │
                  │  router → NL-to-SQL | vector │
                  │  retrieval over insight docs │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌─────────────────────────────┐
                  │ Layer 5: Serving             │
                  │  FastAPI + React, precomputed│
                  └─────────────────────────────┘
```

## Technology choices at a glance

| Concern | Choice | ADR |
|---|---|---|
| Analytical storage | DuckDB (in-process, columnar, reads Parquet natively) | [ADR-001](../adr/ADR-001-duckdb-over-postgres.md) |
| Transformation | dbt-duckdb, staging/intermediate/marts layering | [ADR-002](../adr/ADR-002-dbt-layering.md) |
| Time-series evaluation | Chronological split, never random | [ADR-003](../adr/ADR-003-chronological-split.md) |
| Numeric Q&A | NL-to-SQL executes real queries, not RAG-over-text | [ADR-004](../adr/ADR-004-hybrid-rag-nl-to-sql.md) |
| Deployment | Precomputed artifacts, no live big-data compute | [ADR-005](../adr/ADR-005-precompute-for-deployment.md) |
| AI tooling investment | Full `.claude/` scaffolding despite solo scope | [ADR-006](../adr/ADR-006-ai-tooling-investment.md) |

See [System-Design.md](System-Design.md), [Data-Flow.md](Data-Flow.md),
[Infrastructure.md](Infrastructure.md), [Deployment.md](Deployment.md),
[Security.md](Security.md) for the expanded per-concern docs.
