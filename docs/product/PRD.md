# Product Requirements Document

**Owner:** solo builder. **Status:** Layer 1 in progress. See
[../../.claude/memory.md](../../.claude/memory.md) for current state.

## Problem

A generic "I used pandas + XGBoost on a Kaggle dataset" portfolio project
doesn't demonstrate engineering judgment. There's no visible evidence of:
why a particular storage engine was chosen, whether a from-scratch algorithm
is actually correct, whether a model comparison avoided the classic
time-series leakage mistake, or whether an LLM feature is grounded in real
numbers or just fluent-sounding invention.

## Who this is for

A single persona: **an interviewer or hiring manager evaluating this
person's engineering judgment**, not an end user with a real transportation
need. Every feature is designed to be *explainable in an interview*, not to
maximize DAU. See [Personas.md](Personas.md).

## Functional requirements (mapped to project_plan.md layers)

- FR-1: Load 8-10M rows of HVFHV trip data into DuckDB (Layer 0).
- FR-2: Transform raw trips into tested staging/intermediate/mart tables,
  including `zone_hourly_demand` (ML target), `zone_fare_stats`,
  `zone_pair_flows` (graph input) (Layer 1).
- FR-3: Provide nearest-zone spatial lookup (KD-tree + geohash), zone
  importance ranking (PageRank), and shortest-path ETA (Dijkstra) (Layer 2).
- FR-4: Provide demand forecasts from 4 methods (linear, EWMA, XGBoost,
  LSTM) compared on identical chronological test data, plus a fare
  prediction model (Layer 3).
- FR-5: Answer natural-language questions via a router that sends numeric
  questions to NL-to-SQL and explanatory questions to vector retrieval over
  grounded insight docs (Layer 4).
- FR-6: Serve predictions and chat via FastAPI, visualize via a React map +
  chat + comparison chart, deployed and reachable by a public URL (Layer 5).

## Non-goals

- Real-time data ingestion or live pricing.
- Multi-user auth, billing, or any account system.
- Serving the full 8-10M row pipeline live (see rule 8 in
  [rules.md](../../.claude/rules.md) — precompute for deployment).
- Novel ML research or beating published TLC-demand-forecasting benchmarks.

## Success metrics

See [Success-Metrics.md](Success-Metrics.md).
