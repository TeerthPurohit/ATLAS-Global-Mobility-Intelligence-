# NYC Ride Intelligence — TLC Mobility Platform

An engineer-focused mobility intelligence platform built from NYC Taxi &
Limousine Commission high-volume for-hire trip records — **113M+ rows**,
January/March/June 2024. Full lifecycle: raw ingestion → reproducible
transforms (dbt) → classical algorithms → a model ladder trained and
evaluated honestly → grounded hybrid RAG → a typed FastAPI serving a
Next.js frontend.

**Scope is deliberately one city with real observed data: NYC.** A global,
519-city layer and a second real city (London) both existed at points in
this repo's history and were removed — see
[ADR-011](docs/adr/ADR-011-retreat-from-global-coverage.md) and
[ADR-012](docs/adr/ADR-012-nyc-only.md) for why. A third city is welcome
whenever it arrives with its own real trip corpus, not a population prior.
[ADR-013](docs/adr/ADR-013-collapse-city-id.md) subsequently removed
`city_id` as a route/URL/prop parameter throughout the stack, since only
one city has ever been registered.

## What's actually implemented

- **Ingestion & warehouse** — `scripts/load_raw_to_duckdb.py` loads raw
  HVFHV Parquet into `data/warehouse/nyc_rides.duckdb`.
- **dbt transforms** — staging → intermediate → marts
  (`zone_hourly_demand`, `zone_fare_stats`, `zone_pair_flows`,
  `canonical_areas`) in `dbt_project/`.
- **Classical algorithms, from scratch, validated against reference
  libraries** — KD-tree zone lookup, geohash grid, PageRank hub ranking,
  Dijkstra shortest-path ETA, EWMA smoothing + seasonal decomposition
  (`algorithms/`).
- **Model ladder** — linear → EWMA → XGBoost → LSTM for demand, plus an
  XGBoost fare model, ETA quantiles, and a congestion model
  (`models/`), all on chronological splits — see
  `models/evaluation/metrics_report.md` for real measured numbers.
- **Hybrid RAG** — a router sends numeric questions through a
  schema-agnostic `QueryPlan` compiled to real SQL
  (`rag/nl_to_sql/`, never LLM-generated SQL text) and explanatory
  questions through Qdrant vector retrieval + strictly grounded LLM
  synthesis (`rag/`). Includes reranking, a semantic cache, and a
  fine-tuning baseline for the QueryPlan model (gated off by default,
  paid fine-tune paused per [ADR-010](docs/adr/ADR-010-query-plan-finetuning-budget-exception.md)).
- **Serving** — a typed FastAPI backend (`backend/`) with model artifacts
  and registries preloaded at startup, and a Next.js map-first frontend
  (`frontend-web/`).

## Architecture

```
Layer 0  Ingest            raw HVFHV parquet → DuckDB (scripts/)
Layer 1  dbt transform      staging → intermediate → marts (dbt_project/)
Layer 2  Algorithms         spatial / graph / timeseries (algorithms/)
Layer 3  Model ladder       linear → EWMA → XGBoost → LSTM (models/)
Layer 4  Hybrid RAG         NL→QueryPlan→SQL, vector retrieval (rag/)
Layer 5  Serving            FastAPI (backend/) + Next.js (frontend-web/)
```

Each layer only reads what the previous one produced — the backend never
recomputes a mart, and RAG insight generation reads marts rather than raw
tables. See `.claude/architecture.md` for the full dependency graph and
`docs/architecture/` for detailed diagrams.

## API surface

All routes are mounted bare under `/api/...` or their own top-level prefix
— there is no `city_id` in any route (ADR-013). Representative endpoints:

| Router | Routes |
|---|---|
| `predictions` | `GET /predict/demand`, `GET /predict/fare` |
| `zones` | `GET /zones`, `GET /zones/{zone_id}` |
| `chat` | `POST /chat`, `GET /chat/history/{session_id}`, `WS /chat/stream` |
| `journey` | `POST /journey/estimate`, `GET /journey/history`, `GET /journey/features` |
| `city` | `GET /api/capabilities`, `/api/areas`, `/api/areas/{area_id}`, `/api/metrics`, `/api/forecast`, `/api/profile`, `/api/tariff`, `/api/context` |
| `mobility` | `POST /api/mobility/{route,fare,demand,congestion,availability,surge,carbon,departure-time}` |
| `context` | `GET /api/context/{weather,holiday,traffic}` |
| `analytics` | `GET /api/analytics/{summary,insights,history,trends}` |
| `platform` | `GET /health`, `/dashboard/summary`, `/warehouse/stats`, `/models/metrics`, `/algorithms/benchmarks`, `/pipeline/status`, … |

Full reference: `docs/api/README.md` or `/docs` on a running server.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # set OPENAI_API_KEY, QDRANT_URL, etc.

python scripts/load_raw_to_duckdb.py     # ingest raw Parquet
cd dbt_project && dbt build && cd ..     # build marts

cd backend && uvicorn main:app --reload  # http://localhost:8000
```

```bash
cd frontend-web
npm install
npm run dev                    # http://localhost:3000
```

## Repository layout

`backend/`, `dbt_project/`, `data/`, `models/`, `algorithms/`, `rag/`,
`scripts/`, `frontend-web/`, `docs/`, `specs/` (one spec per layer/feature,
written against `project_plan.md`), `.claude/` (project constitution,
subagents, skills — see `.claude/CLAUDE.md`).

## Docs

- `docs/architecture/` — full system diagrams
- `docs/adr/` — architecture decision records
- `docs/api/` — API reference
- `.claude/memory.md` — living state: what's actually built, right now
- `docs/product/Roadmap.md` — layer-by-layer progress checklist

Render the docs site locally: `pip install -r requirements-docs.txt && mkdocs serve`.

## Testing

```bash
pytest                                   # full suite
pytest tests/test_algorithms.py -v       # one file
```

## License

See `LICENSE` at the repo root.
