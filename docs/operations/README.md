# Operations

## Health / liveness

`GET /health` -- DuckDB + Qdrant liveness, real point checks (not cached
artifacts). `GET /pipeline/status` -- dbt's own `run_results.json`
(per-stage status/timing from the last real `dbt run`).

## Logging (SPEC-013 FR-14)

Stdlib `logging` only, no new infra -- `backend/main.py` configures
`logging.basicConfig(level=INFO)` once at import time. Structured INFO-level
logs exist for:

- **City resolution** -- `backend/registry/cities.py`'s `get_city()` logs
  `city_id -> found/not_found`.
- **Model resolution** -- `backend/registry/models.py`'s `resolve_model()`
  logs `city_id, metric -> model_id or none`; `load()` logs a warning for
  any `model_registry` row whose `artifact_path` is missing on disk.
- **Capability checks** -- `backend/registry/cities.py`'s
  `get_capabilities()` logs the full computed capability dict per request.
- **Query-plan compilation** -- `rag/nl_to_sql/query_plan_compiler.py`
  logs the compiled SQL (via `sql_agent.py`'s call site) for every chat
  numeric-question turn.
- **Prediction provenance** -- `backend/services/prediction_service.py`
  logs which model actually answered a city-scoped prediction request.

## Known operational gaps (honest, not hidden)

- No metrics/tracing stack (Prometheus/OTel) -- solo-project scope (rule 7),
  add when a real incident makes the gap bite, not speculatively.
- `/forecast` returns a real historical hourly aggregate, explicitly labeled
  as not a forward time-series forecast -- no live retraining or streaming
  update path exists yet.
- The RAG chat pipeline (`rag/rag_pipeline.py`) is still NYC-only; `city_id`/
  `area_id` on `ChatRequest`/`ChatResponse` are context fields only this
  phase (SPEC-013 FR-11), not yet used to route to a different city's data.
