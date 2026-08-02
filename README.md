# NYC TLC Trip Data — Analytics & ML Platform

An end-to-end data platform for the **New York City TLC Trip Record Data**.  
Ingests public parquet datasets, transforms them with **dbt + DuckDB**, trains forecasting / fare-prediction models, surfaces insights via a **RAG pipeline**, and serves results through a **FastAPI backend + React frontend**.

---

## Project Structure

```
├── data/               # Raw parquet files, lookups, DuckDB warehouse
├── dbt_project/        # dbt transformations (staging → intermediate → marts)
├── algorithms/         # Spatial, graph, and time-series algorithms
├── models/             # ML models (XGBoost, LSTM, fare prediction, evaluation)
├── rag/                # Retrieval-Augmented Generation pipeline
├── backend/            # FastAPI application
├── frontend/           # React UI
├── notebooks/          # Jupyter notebooks (EDA, exploration)
├── docs/               # Architecture docs & overview
└── tests/              # Unit & integration tests
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env

# 3. Ingest & transform data (via DuckDB + dbt)
#    (run ingestion scripts, then dbt build)

# 4. Launch the backend
cd backend && uvicorn main:app --reload

# 5. Launch the frontend
cd frontend && npm install && npm run dev
```

## Tech Stack

| Layer           | Technology                         |
|-----------------|------------------------------------|
| Warehouse       | DuckDB                             |
| Transform       | dbt-core + dbt-duckdb              |
| ML              | XGBoost, PyTorch (LSTM), scikit-learn |
| RAG / NL→SQL   | LangChain / LlamaIndex             |
| Backend API     | FastAPI                            |
| Frontend        | React (Vite)                       |
| Containers      | Docker / docker-compose            |

## Why DuckDB?

DuckDB is an in-process, vectorized OLAP database built for analytics on a single machine. Unlike row-store engines such as Postgres or SQLite, DuckDB uses columnar storage and batch processing to scan millions of rows in seconds — without needing a server. It reads Parquet files natively, meaning the raw TLC data stays in its efficient columnar format on disk and is loaded directly into DuckDB's engine with zero pandas round-trips. At ~387 MB for 8M rows it stays laptop-manageable while delivering the query speed of a much heavier warehouse for this project's scale.
