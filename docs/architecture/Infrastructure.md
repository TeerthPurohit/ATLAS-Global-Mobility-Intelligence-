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

- Backend: a single AWS EC2 instance (`t4g.small`, Graviton/ARM64) running
  FastAPI behind Caddy (auto-TLS) via Docker Compose, with a **read-only,
  precomputed** copy of the DuckDB file (marts + prediction tables only —
  not the 8-10M row raw trips table) baked into the image. Chosen over
  ECS/Fargate+ALB (~3x the monthly cost for a single-task, no-autoscaling
  deployment) and over staying on the Oracle Always-Free VM already running
  the QueryPlan model (chosen for AWS's resume value, a deliberate
  cost-vs-signal tradeoff) — see ADR-014. Infra is defined in
  `infra/cdk/backend_stack.py`: one EC2 instance in the default VPC's
  public subnet (no NAT gateway — a stateless single instance has no need
  to hide behind one), an Elastic IP, an ECR repo, an IAM instance role
  scoped to SSM Session Manager (no SSH key pair) + ECR pull, and an
  OIDC-federated GitHub Actions role (no static AWS keys) for
  `.github/workflows/deploy-backend-aws.yml`. Postgres (Neon, pooled
  endpoint) and vector search (Qdrant Cloud) are both external managed
  free-tier services, not self-hosted on this instance.
- Frontend: Vercel, talks to the backend over HTTPS.
- No message queue, no cache layer, no self-hosted vector store — Qdrant
  Cloud's free tier is the real target (`QDRANT_URL`/`QDRANT_API_KEY`); the
  local `qdrant` container in `docker-compose.yml` is a dev-only
  convenience, not what production runs.

## What's explicitly out of scope

Auto-scaling, multi-region, blue/green deploys, secrets manager beyond
`.env`, observability stack (Grafana/Prometheus) — all team/production
concerns this repo doesn't have. If any of these become genuinely needed,
record why in a new ADR before adding it (see rule 7 in
`.claude/rules.md`).
