# Getting Started

Local dev setup for the NYC Ride Intelligence / Global Mobility Intelligence
platform. See [`docs/architecture/`](../architecture/) for system design,
[`docs/api/`](../api/) for the live route reference.

## Prerequisites

- Python 3.11+ (repo tested on 3.12), Node 18+ for the frontend
- `pip install -r requirements.txt` (training/dbt/notebook deps) or
  `pip install -r requirements-backend.txt` (serving-only, matches
  `backend/Dockerfile`)
- Copy `.env.example` -> `.env` and fill in `OPENAI_API_KEY` (chat/RAG).
  Weather needs no key -- the Open-Meteo adapter is keyless, and degrades
  honestly to `basis="unavailable"` if unreachable.

## Build the warehouse

```bash
python scripts/load_raw_to_duckdb.py     # raw HVFHV parquet -> data/warehouse/nyc_rides.duckdb
cd dbt_project && dbt seed && dbt run && dbt test
python scripts/generate_algorithm_artifacts.py   # KD-tree benchmark + PageRank hubs, real artifacts
```

`dbt`'s DuckDB path is `data/warehouse/nyc_rides.duckdb`, resolved relative
to wherever `dbt` is invoked from -- set `DUCKDB_PATH` to an absolute path if
running from a directory other than `dbt_project/`.

## Run the backend

```bash
cd backend && uvicorn main:app --reload
```

`backend/main.py`'s `lifespan` hook loads every model artifact and registry
table once before the app accepts traffic (rule 8 -- no training or raw-table
scans on a request path). Interactive OpenAPI docs at `/docs`.

## Run the frontend

```bash
cd frontend && npm install && npm run dev
```

## Run tests

```bash
pytest tests/ -q
```

Most API/journey/registry tests skip automatically if the warehouse hasn't
been built yet (`pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), ...)`).

## Docker

`docker-compose.yml` runs the full stack (backend, frontend, Qdrant for RAG
embeddings) -- see [`docs/deployment/`](../deployment/).
