# Infrastructure

Deliberately minimal — this is a free-tier-hostable solo project, not a
platform with an SRE budget.

## Local / build time

- DuckDB file on disk, no server process.
- dbt-duckdb adapter, run from the CLI (`dbt run`, `dbt test`).
- Python virtualenv (`.venv/`) for algorithms/models/rag/backend.
- Node/npm for `frontend/`.
- No containers required for local dev; `docker-compose.yml` exists to make
  the whole stack reproducible for someone else running it, not because
  local dev needs isolation.
- **`dbt build` itself no longer runs on the local machine.** At 113M+ rows
  (`int_trips_enriched` and downstream marts), a full build exceeds the dev
  machine's free RAM/disk. Per ADR-009, `dbt build` runs on an on-demand,
  self-terminating EC2 instance, launched manually via the
  `.github/workflows/dbt-build-aws.yml` `workflow_dispatch` job — never
  scheduled, never always-on. Infra is defined in `infra/cdk/` (CDK,
  Python): one S3 bucket (`raw/` input, `warehouse/` output), an IAM role
  for the build instance, an OIDC-federated IAM role for GitHub Actions (no
  static AWS keys), and an outbound-only security group. This changes only
  *where the build runs* — DuckDB is still the engine (ADR-001), dbt SQL is
  unchanged, and the deployed backend still reads a precomputed, read-only
  DuckDB file as described below.

## Deployment target

- Backend: a single free-tier host (Render/Railway per `project_plan.md`)
  running FastAPI, with a **read-only, precomputed** copy of the DuckDB file
  (marts + prediction tables only — not the 8-10M row raw trips table).
- Frontend: static hosting (Vercel/Netlify), talks to the backend over
  HTTPS.
- No message queue, no cache layer. Vector store: Qdrant by default; a
  DuckDB cosine-similarity table is the lighter-footprint fallback for
  deployments where running a separate service isn't worth it, per
  `project_plan.md` Layer 4.

## What's explicitly out of scope

Auto-scaling, multi-region, blue/green deploys, secrets manager beyond
`.env`, observability stack (Grafana/Prometheus) — all team/production
concerns this repo doesn't have. If any of these become genuinely needed,
record why in a new ADR before adding it (see rule 7 in
`.claude/rules.md`).
