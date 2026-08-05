# ADR-001: DuckDB over Postgres for the analytical warehouse

**Status:** Accepted (Layer 0, done)

## Context

Need to hold 8-10M rows of HVFHV trip data and run analytical (OLAP) queries
— aggregations across millions of rows grouped by zone/hour — as the
foundation for dbt marts, algorithms, and ML feature building.

## Decision

Use DuckDB, not Postgres (or any row-store RDBMS).

## Why

- **Columnar vs row storage:** Postgres stores rows contiguously, so an
  aggregation touching 3 of 20 columns still reads all 20 from disk per row.
  DuckDB stores columns contiguously, so a `GROUP BY zone, hour` query only
  reads the columns it needs — dramatically less I/O at this row count.
- **Vectorized execution:** DuckDB processes batches of column values per
  CPU instruction instead of row-by-row, which is why it's fast for exactly
  this workload (large aggregations), not for high-concurrency
  single-row transactional writes.
- **In-process, no server:** no daemon to run, configure, or keep alive — a
  single `.duckdb` file, opened directly by dbt, Python scripts, and (at
  serve time) the backend. Removes an entire category of local-dev and
  free-tier-deployment friction a Postgres server would add.
- **Native Parquet reads:** `read_parquet()` queries TLC's parquet files
  directly, no separate load/ETL step required to get analytical SQL over
  them.

## Consequences

- No concurrent multi-writer support — acceptable, there's one writer (the
  build pipeline), never concurrent user writes.
- Not the right choice if this were a transactional system with many small
  concurrent writes — it isn't; it's read-heavy analytics.
