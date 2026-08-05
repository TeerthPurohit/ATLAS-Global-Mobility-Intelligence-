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
