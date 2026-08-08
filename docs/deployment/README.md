# Deployment

Full deployment design lives in
[`docs/architecture/Deployment.md`](../architecture/Deployment.md) and
[`docs/architecture/Infrastructure.md`](../architecture/Infrastructure.md) --
not duplicated here, this page is the short pointer + what actually exists
on disk today.

## What exists

- `docker-compose.yml` -- backend, frontend, Qdrant (RAG vector store)
- `backend/Dockerfile`, `frontend/Dockerfile`
- `.dockerignore`
- `requirements-backend.txt` -- serving-only dependency set (no torch/dbt/
  scikit-learn/scipy/networkx/jupyter/matplotlib/pytest -- those stay in
  `requirements.txt` for training/dbt/notebook work, which has no place in
  the deployed API image)

## Precompute discipline (rule 8, ADR-005)

The deployed backend never runs the 8-10M row pipeline on a request.
`backend/main.py`'s `lifespan` hook loads every model artifact and registry
table once before the app accepts traffic; every `backend/registry/*.py`
and `backend/services/*.py` module either loads a precomputed artifact at
startup or runs a cheap point query against an already-aggregated mart --
never a raw-table scan or retraining call.

## Target host

Free-tier-friendly (Render/Railway/Vercel per the original project plan) --
not yet provisioned; see `.claude/memory.md`'s "Open questions" section for
current status.
