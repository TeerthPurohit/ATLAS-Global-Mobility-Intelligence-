# System Design

## Components

- **DuckDB file** (`data/warehouse/nyc_rides.duckdb`) — the single source
  of truth for all transformed data. Not a service; it's a local file
  opened in-process by dbt, algorithm scripts, model training scripts, and
  (at serving time) a read-only copy the backend loads precomputed tables
  from.
- **dbt project** — the only place that writes to the warehouse's
  staging/intermediate/marts schemas.
- **Algorithm scripts** (`algorithms/`) — read marts, write nothing back to
  DuckDB; output is either printed/plotted (portfolio artifacts) or saved
  as a feature file consumed by Layer 3.
- **Model training scripts** (`models/`) — read marts + algorithm feature
  outputs, write trained artifacts (`.pkl`, `.pt`) to disk. Training is
  offline, not a service.
- **RAG pipeline** (`rag/`) — `rag_pipeline.py` is the single entry point;
  everything else is a component it calls. Router decides SQL vs retrieval.
- **Vector store** — Qdrant is the default (a DuckDB cosine-similarity table
  is the lighter-footprint fallback if running a separate service isn't
  worth it). Populated by `rag/embeddings/build_vector_store.py`, queried by
  `rag_pipeline.py`'s retrieval path. Not written to by any other component.
- **Backend** (`backend/`) — FastAPI, stateless, loads precomputed
  artifacts at startup, never trains or reprocesses on request.
- **Frontend** (`frontend/`) — React, talks only to the backend's REST API.

## Component boundaries (who owns writing what)

| Data | Written by | Read by |
|---|---|---|
| Raw table | `scripts/load_raw_to_duckdb.py` | dbt staging models only |
| Marts | dbt | algorithms, models, RAG, backend (read-only) |
| Algorithm outputs (feature files) | `algorithms/` scripts | `models/data_prep/build_features.py` |
| Trained model artifacts | `models/*/train_*.py` | `backend/services/model_service.py` |
| RAG insight docs + vector store (Qdrant, or DuckDB table as fallback) | `rag/insight_generation`, `rag/embeddings` | `rag/rag_pipeline.py` |

No component reads from a layer that hasn't been computed yet, and no
component writes to a layer above it (see `.claude/architecture.md`'s
dependency graph rule).

## Why this shape

Each layer is independently testable and independently explainable — you
can point to `algorithms/graph/pagerank_hubs.py` in isolation and defend it
without needing the ML layer to exist. That's a deliberate tradeoff against
a more "integrated" design that would be harder to reason about in pieces.
