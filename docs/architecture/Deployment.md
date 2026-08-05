# Deployment

## Process (Layer 5, not yet executed — this is the plan)

1. Precompute everything the live app needs: marts, model predictions
   (or the model artifacts small enough to load at request time), RAG
   vector store (Qdrant, or a DuckDB table if the fallback is used) and
   insight docs.
2. Copy only the precomputed tables into a slimmed DuckDB file for the
   deployed backend — never ship the raw 8-10M row trips table.
3. Deploy `backend/` to Render or Railway free tier. Set env vars from
   `.env.example` (never commit `.env`).
4. Deploy `frontend/` to Vercel or Netlify, pointed at the deployed backend
   URL.
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
