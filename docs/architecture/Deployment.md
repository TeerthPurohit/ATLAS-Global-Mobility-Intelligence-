# Deployment

## Process (Layer 5 — live)

1. Precompute everything the live app needs: marts, model predictions
   (or the model artifacts small enough to load at request time), RAG
   vector store (Qdrant, or a DuckDB table if the fallback is used) and
   insight docs.
2. Run `scripts/build_deployed_duckdb.py` to copy only the precomputed
   tables into `data/warehouse/deployed.duckdb` — never ship the raw
   8-10M row trips table. `backend/Dockerfile` lands it at the canonical
   `data/warehouse/nyc_rides.duckdb` path. This is a manual step, not part
   of any CI pipeline — re-run it after any marts/model-registry change
   (ADR-005).
3. Deploy `backend/` to an AWS EC2 instance (`infra/cdk/backend_stack.py`,
   ADR-014) via `.github/workflows/deploy-backend-aws.yml`
   (`workflow_dispatch`, manual — never automatic on push, same reasoning
   as step 2). Set env vars in `/opt/app/.env` on the instance from
   `.env.example` (never commit `.env`; see `Infrastructure.md` — a
   secrets manager beyond `.env` is deliberately out of scope for now).
   `docker-compose.oracle.yml` remains the deployment path for the
   Oracle Always-Free VM already running the QueryPlan model, unchanged.
4. Deploy `frontend-web/` to Vercel, pointed at the deployed backend URL.
5. Smoke-test both UC-3 (numeric) and UC-4 (explanatory) chat paths against
   the live URL before calling it done.
6. Record a short demo GIF/video as a backup artifact — free-tier hosts can
   go cold or get decommissioned; the README should not depend on the demo
   always being up.

## Rollback

Given the scale (solo, no traffic SLA), rollback is "redeploy the previous
git commit" — no blue/green, no feature flags. This is intentional; see
[Infrastructure.md](Infrastructure.md) on what's out of scope and why.

## Config

All deployment config comes from environment variables documented in
`.env.example`. No secrets committed to the repo — verify this on every
commit that touches `.env`-adjacent files (this is also enforced by the
top-level git-safety instructions Claude Code always follows).
