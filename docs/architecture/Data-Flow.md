# Data Flow

## Batch flow (build time, run manually / via `dbt run` + training scripts)

```
raw parquet
  → DuckDB raw table                          (scripts/load_raw_to_duckdb.py)
  → stg_trips, stg_zones                      (dbt staging)
  → int_trips_enriched                        (dbt intermediate: joins, hour_of_day,
                                                 day_of_week, is_weekend, trip_duration,
                                                 avg_speed_mph)
  → zone_hourly_demand / zone_fare_stats /
    zone_pair_flows                           (dbt marts)
  → algorithm outputs                         (KD-tree index, PageRank scores,
                                                 EWMA-smoothed series — Layer 2)
  → feature table                             (models/data_prep/build_features.py:
                                                 hour, dow, is_weekend, lag_1h/24h/168h,
                                                 EWMA value, 7-day rolling avg)
  → chronological train/val/test split        (models/data_prep/train_test_split.py)
  → trained artifacts                         (xgboost_demand.pkl, lstm_demand.pt, ...)
  → RAG insight docs, grounded in the above    (rag/insight_generation)
  → vector store: Qdrant, or DuckDB cosine-
    similarity table as a lighter fallback     (rag/embeddings)
```

## Request flow (serve time)

```
Numeric question  → query_classifier.py → nl_to_sql/sql_agent.py
                     → generates SQL against mart schema (schema only, not raw rows)
                     → executes on DuckDB → returns number + SQL shown

Explanatory question → query_classifier.py → vector search (Qdrant, or
                          DuckDB fallback) → retrieves grounded insight
                          doc(s) → LLM phrases the answer using only the
                          retrieved numbers

Prediction request → backend/routers/predictions.py → model_service.py
                      (in-memory artifact, loaded once at startup) → response
```

## Key invariant

Nothing in the request-flow path re-runs dbt, re-trains a model, or scans
raw trip-level rows. Everything the API serves was computed in the batch
flow ahead of time. See rule 8 in `.claude/rules.md` and
[ADR-005](../adr/ADR-005-precompute-for-deployment.md).
