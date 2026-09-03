# ADR-005: Precompute for deployment, never run the full pipeline live

**Status:** Accepted and implemented — `backend/Dockerfile`,
`scripts/build_deployed_duckdb.py`, and `tests/test_serving_artifact.py`
are real, working code (2026-09-02 measured: 12.0 GB → 212 MB). See
[ADR-014](ADR-014-aws-ec2-backend-serving.md) for where the resulting
image is deployed.

## Context

Free-tier hosts (Render/Railway/Vercel-class) have limited CPU, memory, and
often spin down on idle. The full pipeline (raw parquet → dbt → algorithms →
model training) processes 8-10M rows and would be far too slow and too
heavy to run per-request or even per-cold-start.

## Decision

The deployed backend loads only precomputed artifacts: mart tables (not raw
trips), trained model files (`.pkl`/`.pt`), and the RAG vector store
(Qdrant, or a DuckDB cosine-similarity table as a lighter fallback) plus
insight docs. No dbt run, no model training, no raw-table scan happens on
any request path.

## Why

This is a cost/scale tradeoff, not a shortcut: it demonstrates the
engineering judgment to separate "batch compute" from "serving," which is
exactly how a real production system would be built once volume exceeds
what fits in a single request's latency budget — just applied here because
of hosting constraints rather than production QPS.

## Consequences

- The deployed DuckDB file is a small, precomputed slice, not the full
  warehouse — regenerating it after a marts/model change is a manual
  redeploy step (see `docs/architecture/Deployment.md`), not automatic.
- Any "live" feeling in the demo (e.g. NL-to-SQL) is real SQL against real
  precomputed marts, not simulated — the constraint is about not
  reprocessing raw data, not about faking responses (that would violate
  rule 2 in `.claude/rules.md`).
