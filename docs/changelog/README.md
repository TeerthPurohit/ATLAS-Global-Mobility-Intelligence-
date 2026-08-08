# Changelog

Dated entries mirror `.claude/memory.md`'s "Current state" history -- the
canonical source if these ever drift; this page exists for a reader who
wants the story in order without loading the whole memory file.

## 2026-08-08 -- Global Mobility Domain Model, Phase 1 (SPEC-013)

Country -> City -> Area/Metric/Prediction registry, additive, NYC as the
one real city. `dbt_project/seeds/{countries,cities,model_registry}.csv` +
`canonical_areas.sql` mart; `backend/registry/{countries,cities,models}.py`;
`backend/datasources/{base,nyc_tlc}.py`;
`backend/services/prediction_service.py`; new `/api/countries/*`,
`/api/cities/*` routers; `ErrorCode`/`ErrorResponse` taxonomy; NL-to-SQL
restructured onto a `QueryPlan` (SPEC-013 FR-10, built on top of SPEC-014's
concurrently-developed `query_plan.py`/`query_plan_compiler.py`/
`nyc_schema.py`) so the LLM never emits SQL text on the live `/chat` path.
Every pre-existing endpoint verified byte-for-byte behavior-identical by
test. See `.claude/memory.md`'s "Global Mobility Domain Model" section for
the full breakdown.

## 2026-08-07 -- Journey Intelligence Engine, Phase 1 (SPEC-012)

`POST /journey/estimate` -- provider-independent single-trip estimate
(fare/ETA/distance/weather/availability/surge/carbon/AI recommendation).
`backend/predictors/` (`PredictionResult` with a structural `basis` field),
`backend/adapters/` (weather/holiday/routing, free-tier, honest stubs for
paid-only sources), `vehicle_profiles.csv` seed, `journey_narrative.py`.

## 2026-08-06 -- Layer 5 frontend architecture audit

Found ~28 of ~55 dashboard widgets hardcoded despite claiming live
provenance, 3 fabricated (multiplying a real prediction by invented
constants), 2 citing artifacts that didn't exist. All fixed --
`ARCHITECTURE_AUDIT.md` has the full before/after. New
`backend/routers/platform.py` + `backend/services/platform_service.py`,
real `algorithms/*/output/*.json` artifacts via
`scripts/generate_algorithm_artifacts.py`.

## Layers 0-4 -- Data foundation through Hybrid RAG

Raw HVFHV parquet -> DuckDB, dbt staging/intermediate/marts, from-scratch
KD-tree/PageRank/Dijkstra/EWMA (each validated against a reference
library), the EWMA -> linear -> XGBoost -> LSTM demand ladder plus a fare
XGBoost model (chronological split, ADR-003), and the hybrid RAG chat layer
(NL-to-SQL + retrieval-grounded explanatory answers). See
`docs/data/`, `docs/algorithms/`, `docs/models/` for the current-state
summary of each.
