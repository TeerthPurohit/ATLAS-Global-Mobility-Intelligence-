# Deployment

Full deployment design lives in
[`docs/architecture/Deployment.md`](../architecture/Deployment.md) and
[`docs/architecture/Infrastructure.md`](../architecture/Infrastructure.md) --
not duplicated here, this page is the short pointer + what actually exists
on disk today.

## What exists

- `docker-compose.yml` -- backend, frontend, Qdrant (RAG vector store)
- `docker-compose.oracle.yml` -- Caddy + backend + OSRM, for a single VM
- `backend/Dockerfile`, `frontend/Dockerfile`
- `.dockerignore`
- `requirements-backend.txt` -- serving-only dependency set (no dbt/scipy/
  networkx/jupyter/matplotlib/pytest -- those stay in `requirements.txt` for
  training/dbt/notebook work, which has no place in the deployed API image).
  **torch and scikit-learn are in it**, both as genuine serving deps: torch
  for the LSTM/Transformer demand endpoints, scikit-learn for xgboost's
  `XGBRegressor` wrapper and the RAG reranker's TF-IDF.
- `scripts/build_deployed_duckdb.py` -- builds the slim serving artifact

## Build the serving artifact before deploying

```bash
python scripts/build_deployed_duckdb.py   # -> data/warehouse/deployed.duckdb
```

Copies the 13 mart/reference tables the API actually serves from, and
precomputes the facts derived from the excluded 113M-row tables (row counts
and column schemas for `stg_trips`/`stg_zones`/`int_trips_enriched`, and the
citywide baseline `avg_speed_mph`) into a `serving_metadata` table.

Measured on the current warehouse: **12.0 GB -> 212 MB**. The full warehouse
never enters the build context (`.dockerignore`), and `backend/Dockerfile`
lands the artifact at the canonical `data/warehouse/nyc_rides.duckdb` path so
every service's `WAREHOUSE_PATH` resolves unchanged.

Re-run it after any marts or model-registry change -- that is the manual
redeploy step ADR-005 calls out. `tests/test_serving_artifact.py` verifies the
artifact serves the same facts as the full warehouse.

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
