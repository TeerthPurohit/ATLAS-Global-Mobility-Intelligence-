# NYC Ride Intelligence — TLC Mobility Platform

An engineer-focused mobility intelligence platform built from the NYC Taxi & Limousine Commission trip records — 113M+ rows — enriched with weather, holiday, and tariff data. Scope is deliberately one city with real observed data: see [ADR-011](docs/adr/ADR-011-retreat-from-global-coverage.md) for why the 519-city global layer was removed and [ADR-012](docs/adr/ADR-012-nyc-only.md) for why London followed. The repo demonstrates a complete analytic lifecycle: raw ingestion → reproducible transforms (dbt) → classical algorithms → model training & evaluation → grounded RAG insight generation → serving via a typed FastAPI.

Snapshot & scale

- Primary NYC corpus: **113M+** trip records (Parquet, stored out-of-repo/warehouse by default).
- Canonical zones: ~265 TLC zones (see `data/lookup/zone_centroids.csv`).
- Vector store: insight-docs embedded into Qdrant using OpenAI embeddings (precompute stage).

Project goals

- Reproducible, auditable analytics (DuckDB + dbt).
- Deterministic numeric answers for queries (NL→QueryPlan→SQL) and grounded explanatory narratives (RAG with strict grounding checks).
- A model ladder for demand/fare/ETA (EWMA → linear → XGBoost → LSTM / quantiles).

---

00. Hero / Project identity

Global Mobility Intelligence — a city-aware platform for predicting demand, fares, ETA quantiles, congestion signals, and producing grounded explanations for mobility queries.

01. Executive summary

In 30 seconds: this repo ingests large-scale trip records, builds reproducible analytical marts via dbt, implements validated algorithms (KD-tree zone lookup, PageRank, shortest-path ETA, EWMA), trains a model ladder for demand/fare/ETA, and exposes a guarded hybrid RAG assistant plus typed prediction APIs. Numeric answers come from executed SQL or deterministic model inference; LLMs are used only for short, grounded explanatory synthesis.

02. Why this project exists

Mobility data and intelligence are often city-specific and hard to generalize. This project started as an NYC TLC forecasting/analytics effort and evolved into a city-aware architecture with transfer-based estimation for cities without local history. The repo demonstrates engineering best practices: precompute-heavy transforms, chronological splits for model evaluation, and clear provenance for every numeric output.

03. What the platform does (capability overview)

- Demand forecasting: hourly zone-level demand predictions.
- Fare estimation: pickup→dropoff fare prediction by hour.
- ETA & quantiles: travel-time quantile estimates.
- Congestion & availability signals: derived models and indicators.
- Zone metadata & nearest-zone lookup (KD-tree).
- Hybrid RAG assistant: numeric NL→SQL path + retrieval-backed explanations.
- Precompute and serve: dbt marts, pretrained model artifacts, and vector stores are built offline and served by FastAPI.

04. Platform at a glance (quick metrics)

- Core dataset: 113M+ NYC TLC trip rows
- Zones: ~265
- Major tech: DuckDB, dbt, XGBoost, PyTorch (LSTM), OpenAI embeddings, Qdrant, FastAPI

05. Data scale & ingestion

NYC TLC
- Source: NYC TLC public trip records (Parquet). Raw Parquet files live in `data/raw/` when present.
- Ingestion: `scripts/load_raw_to_duckdb.py` loads/parses Parquet into `data/warehouse/nyc_rides.duckdb`.
- Final marts: produced by `dbt_project/` (notably `zone_hourly_demand`, `zone_pair_flows`, `zone_fare_stats`).

06. Data sources

- Detailed provenance and download instructions are in `docs/data/` and in script headers under `scripts/`. Every seed file and lookup has source and generation metadata.

07. Geographic coverage

One city with real observed trip data: **NYC** — 265 TLC zones, high-volume for-hire records. A city is added only when it brings its own corpus; there is no prior-based coverage.

08. City capability model

Every served city is OBSERVED: local trip history plus trained models. Capability is derived per-field from what is actually wired (`backend/registry/cities.py`'s `capability_matrix`) — a fare needs a trained fare model or a real calibrated tariff, never a tier label. An unregistered `city_id` returns 404 rather than a degraded estimate.

09. System architecture

Layers:
- Ingest: `scripts/` (Parquet → DuckDB)
- Warehouse: DuckDB file (`data/warehouse/nyc_rides.duckdb`)
- Transform: dbt staging → intermediate → marts (`dbt_project/`)
- Algorithms & feature builders: `algorithms/`, `models/*/build_features.py`
- Model training: `models/*/train_*.py` (XGBoost, PyTorch LSTM, quantiles)
- RAG precompute: `rag/insight_generation` → `rag/embeddings` (OpenAI → Qdrant)
- Serving: FastAPI (`backend/`) with typed schemas and preloaded model artifacts

10. End-to-end request flow

Numeric question (safe deterministic path):
1. `router/query_classifier.py` classifies numeric intent
2. `nl_to_sql/sql_agent.py` compiles a QueryPlan → SQL
3. SQL executes against dbt marts in DuckDB → numeric answer returned

Explanatory question (RAG path):
1. Retrieve top-k insight docs from Qdrant
2. Run brief LLM synthesis with strict grounding (no new numbers allowed)
3. If LLM introduces ungrounded numbers, fall back to retrieved doc verbatim

11. Backend architecture (key files)

- `backend/main.py`: FastAPI app and lifespan preloads (`model_service.load()`, registries)
- `backend/routers/`: predictions, zones, chat, journey, analytics, cities, mobility, context, platform
- `backend/services/`: model_service, journey_service, platform_service, rag_service
- `backend/registry/`: city and model registries

12. Frontend architecture

Per your request, frontend implementation details are intentionally omitted here; the API is designed to support map-first or other UI clients but this README focuses on backend, data, models, and architecture.

13. API architecture (representative endpoints)

- `GET /predict/demand` — demand prediction (XGBoost fallback to EWMA)
- `GET /predict/fare` — fare prediction (XGBoost / tariff fallback)
- `GET /zones` — list zones (~265)
- `GET /zones/{zone_id}` — zone metadata
- `POST /chat` — hybrid RAG assistant (numeric/explanatory)
- `GET /chat/history/{session_id}` — session history
- `WS /chat/stream` — streaming chat responses

Refer to `docs/api/` for full route documentation and OpenAPI rendering.

14. Prediction architecture

- Artifacts saved under `models/` (XGBoost JSONs, PyTorch state for LSTM, quantile artifacts)
- Models loaded at FastAPI lifespan start to avoid on-request I/O (`backend/main.py`)
- Chronological split utilities and feature builders are in `models/data_prep/` and `models/*/build_features.py`.

15. Fare, demand, routing & congestion (summary)

- Fare: `models/fare_prediction` contains train + metadata + tariff profile generation
- Demand: XGBoost demand model (`models/xgboost_model`), EWMA and linear baselines
- Routing & ETA: algorithms in `algorithms/graph`, ETA quantiles in `models/eta`
- Congestion: `models/congestion`

16. Confidence & provenance

All numeric responses indicate the source (model name or SQL/mart). The RAG pipeline validates that any LLM-produced text only reuses numbers present in retrieved docs; otherwise the system returns the original retrieved text.

17. AI / RAG architecture

- Insight docs: `rag/insight_generation/generate_insight_docs.py` → JSONL output
- Embeddings: OpenAI `text-embedding-3-small` used during precompute
- Vector store: Qdrant (docker-compose service)
- Retrieval & synthesis: `rag/rag_pipeline.py` ties classifier → vector search → guarded LLM synthesis

18. Data engineering / dbt

- `dbt_project/` contains staging models and marts. Key mart: `zone_hourly_demand` (`dbt_project/models/marts/zone_hourly_demand.sql`).
- Run `dbt build` to materialize marts used by the API and models.

19. Database architecture

- DuckDB: analytical warehouse file per environment (`data/warehouse/nyc_rides.duckdb`)
- Qdrant: vector store for insight docs

20. ML models (detailed list)

- EWMA baseline (`models/ewma_baseline`)
- Linear baseline (`models/linear_baseline`)
- XGBoost demand (`models/xgboost_model`) and fare (`models/fare_prediction`)
- LSTM sequence model (`models/lstm_model`)
- ETA quantiles (`models/eta`)

21. Model training & evaluation

Training scripts and evaluation artifacts are present under `models/*`. Evaluation reports and comparison artifacts are under `models/evaluation/` (`metrics_report.md`, `compare_results.json`). Reproduce metrics by running the training + evaluation scripts.

22. How good are the models?

Measured model metrics are kept as artifacts (see `models/evaluation/`). The README intentionally links to artifact files instead of summarizing numbers here to avoid stale claims.

23. API examples

Demand example:

```bash
curl 'http://localhost:8000/predict/demand?zone_id=79&hour=18&day_of_week=4'
```

Chat example:

```bash
curl -X POST http://localhost:8000/chat -H 'Content-Type: application/json' -d '{"question": "Why is JFK so busy at noon?"}'
```

24. Running locally (quick start)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# configure OPENAI_API_KEY, QDRANT_URL as needed
python scripts/load_raw_to_duckdb.py  # optional: small sample or full ingestion
cd dbt_project && dbt build
cd backend && uvicorn main:app --reload
```

25. Production readiness

Ready components:
- Typed FastAPI with preloaded artifacts and structured error handling
- Deterministic numeric path (NL→QueryPlan→SQL)
- Reproducible dbt transforms and precompute discipline

Work remaining for full production:
- Automated pipeline orchestration and retraining schedules
- Model monitoring and drift detection
- Expanded per-city model coverage

26. Current limitations

- High-fidelity coverage primarily for NYC; other cities vary in fidelity
- Not all zones have insight-docs for RAG explanations yet
- Real-time traffic/availability is not implemented (no live feed; see ADR-008)

27. Roadmap

- Short-term: automate retraining, add more insight docs, expand transfer-based coverage
- Mid-term: per-city model rollout, model monitoring, continuous evaluation

28. Repository structure

See the repo tree for details; key folders: `backend/`, `dbt_project/`, `data/`, `models/`, `algorithms/`, `rag/`, `scripts/`, `docs/`.

29. Documentation

Render docs locally:

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

30. Contributing

Fork, branch, run tests (`pytest`), and open a PR. See `docs/` for development conventions.

31. License

See `LICENSE` at the repo root.

Technical highlights

- DuckDB + dbt for reproducible analytics
- Deterministic NL→QueryPlan→SQL numeric path
- Grounded RAG with OpenAI embeddings + Qdrant
- XGBoost & LSTM model ladder; EWMA & linear baselines
- From-scratch algorithms validated against references (KD-tree, PageRank, Dijkstra, EWMA)

---

If you'd like, I can (pick one):
- run a repo-wide grep to confirm no leftover frontend instructions,
- split this README into the numbered section files you suggested under `docs/README_SECTIONS/`, or
- generate `docs/QUICK_START.md` with ready-to-copy onboarding commands.

---

## High-level architecture

- **Ingest & warehouse:** raw Parquet files are stored under `data/raw/` and loaded into an on-disk DuckDB warehouse (see `scripts/load_raw_to_duckdb.py`).
- **Transform (dbt):** a layered dbt project (staging → intermediate → marts) lives in `dbt_project/` and produces reproducible analytic tables used by models and the API.
- **Algorithms:** classical algorithm implementations live in `algorithms/` (KD-tree, PageRank, Dijkstra, EWMA) and are validated against reference libraries.
- **Model ladder:** models (`models/`) include linear baselines, EWMA, XGBoost, and an LSTM; training and evaluation notebooks live in `notebooks/` and model artifacts are loaded at backend startup by `backend/main.py` (see `model_service.load()`).
- **RAG & embeddings:** the `rag/` folder contains code for building embeddings, vector stores (qdrant in compose), and the hybrid retrieval + NL→SQL routing pipeline used to surface narrative insights.
- **Serving:** a FastAPI backend (`backend/`) exposes prediction, zones, journey, and analytics endpoints. The API serves precomputed artifacts and model outputs.

## What data we use and how it's constructed

- Source: public NYC TLC trip-record Parquet files (stored in `data/raw/`).
- Ingestion: `scripts/load_raw_to_duckdb.py` and other scripts under `scripts/` load/normalize Parquet into the DuckDB warehouse in `data/warehouse/`.
- Transformation: `dbt_project/` contains staging models to normalize columns, intermediate models enriching trips with weather, holidays, geographic joins and finally marts that power models and API endpoints.
- Lookups/seeds: `data/lookup/` contains zone lookups, tariff profiles, and other small reference tables used as dbt seeds.

## Quick start — local development

1) Create and activate a Python virtualenv, then install runtime deps:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

2) Copy environment variables and set keys (OpenAI, OpenWeather, etc.):

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY, etc.
```

3) (Optional) Run docs site locally:

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

4) Ingest data and run dbt (point dbt profiles to your DuckDB warehouse):

```bash
python scripts/load_raw_to_duckdb.py
cd dbt_project
dbt build
```

5) Start the backend (loads models on startup):

```bash
cd backend
uvicorn main:app --reload
```

## Key implementation notes

- The backend preloads model artifacts and registries during the FastAPI lifespan (see `backend/main.py`) to avoid on-request training or heavy I/O.
- Classical algorithms in `algorithms/` are implemented from-scratch and validated against reference implementations to ensure correctness.
- The project follows a precompute discipline: heavy transforms, model training, and vector-store builds are performed offline via scripts and dbt; the API serves precomputed artifacts.

## Tests, docs, and development resources

- Tests live in `tests/` and are runnable with `pytest`.
- The docs site is under `docs/` and renders via `mkdocs` (`requirements-docs.txt`).
- API reference and routers live in `backend/routers/` and `docs/api/`.

---

## Where to look next

- Read the architecture overview: `docs/architecture/`.
- See ingestion scripts: `scripts/` (e.g. `load_raw_to_duckdb.py`).
- Backend entrypoint and lifespan load: `backend/main.py`.
- RAG pipeline: `rag/` and `rag/embeddings/`.

If you'd like, I can also run tests, render the docs site locally, or add a short `docs/QUICK_START.md` with copy-paste commands for new contributors.

**Capabilities (what's implemented in this repo)**

- Data & ETL:
	- Raw Parquet ingestion into a DuckDB warehouse (`scripts/load_raw_to_duckdb.py`).
	- dbt project producing marts such as `zone_hourly_demand`, `zone_pair_flows`, and `zone_fare_stats` (`dbt_project/models/marts/`).
- Algorithms (from-scratch + validated): KD-tree zone lookup, geohash grid, PageRank hub/rank analysis, shortest-path ETA / route graph construction, EWMA smoothing and seasonal decomposition (`algorithms/`).
- Models:
	- Baselines: EWMA and linear baselines (`models/ewma_baseline`, `models/linear_baseline`).
	- XGBoost demand and fare models with feature builders and training scripts (`models/xgboost_model`, `models/fare_prediction`).
	- LSTM sequence model and training pipeline (`models/lstm_model`).
	- ETA quantile models and congestion model artifacts (`models/eta`, `models/congestion`).
- Data engineering & modeling discipline:
	- Chronological train/test splits, precompute-heavy transforms, and model artifacts persisted and loaded at startup (`models/data_prep`, `backend/main.py`).
- Hybrid RAG (retrieval + controlled LLM synthesis):
	- Numeric path: NL→QueryPlan→`nl_to_sql/sql_agent.py` compiles real SQL which is executed directly (no LLM-generated numbers).
	- Explanatory path: insight-doc generation, vectorization with OpenAI embeddings, storage in Qdrant, retrieval + guarded LLM synthesis (`rag/insight_generation`, `rag/embeddings`, `rag/rag_pipeline.py`).
	- Vector store build and search using OpenAI `text-embedding-3-small` and `qdrant-client` (`rag/embeddings/build_vector_store.py`).
- API surface (FastAPI):
	- Prediction endpoints: `/predict/demand`, `/predict/fare` (`backend/routers/predictions.py`).
	- Zone metadata: `/zones` and `/zones/{zone_id}` (`backend/routers/zones.py`).
	- Hybrid chat: `/chat` (POST), `/chat/history/{session_id}`, and WebSocket streaming (`backend/routers/chat.py`).
	- Additional routers for journeys, analytics, cities, mobility, platform, and context (`backend/routers/`).

This list is grounded in the repository files and docs; if you want, I can expand any capability into a short README subsection with usage examples and commands to re-run the precompute steps that generate the artifacts.

