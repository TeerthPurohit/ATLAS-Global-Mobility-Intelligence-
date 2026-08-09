# Colab training notebooks

Thin runners only. Every cell calls straight into `models/xgboost_model`,
`models/congestion`, `models/eta`, `models/global_transfer` — no training
logic is duplicated here. Use these when local hardware can't handle a
bigger sample than the committed artifacts were trained on.

- `01_nyc_demand_congestion_eta.ipynb` — NYC zone-hourly demand, congestion
  multiplier, quantile ETA (p10/p50/p90).
- `02_global_transfer.ipynb` — the joint NYC+London global transfer demand
  model (`models/global_transfer/train_global.py`).

## Getting the DuckDB file into Colab

`data/warehouse/nyc_rides.duckdb` is 6.0 GB and `data/warehouse/
london_cycles.duckdb` is ~0.22 GB (both measured locally, not estimated) —
too large to commit to git, so `git clone` inside the notebook only gets
code. Get the data there separately, either way works:

- **Google Drive**: upload the `.duckdb` file(s) into any Drive folder,
  mount Drive in the notebook (cell 1), point `GLOBAL_MOBILITY_DATA_ROOT` at
  that folder.
- **GCS**: `gsutil cp gs://<bucket>/nyc_rides.duckdb /content/data/` inside
  the notebook, then set `GLOBAL_MOBILITY_DATA_ROOT=/content/data`.

## Env vars

- `GLOBAL_MOBILITY_DATA_ROOT` — folder containing the `.duckdb` file(s).
  Never hardcoded to one person's Drive layout; each notebook symlinks the
  real file into the exact path the training scripts already expect
  (`<repo>/data/warehouse/<name>.duckdb`).
- `GLOBAL_MOBILITY_REPO_URL` — optional, defaults to a placeholder; set it
  to your own fork/clone URL.

## Progressive-sampling workflow (applies to notebook 01's congestion + ETA
cells — NYC demand and the global transfer model already train on small
pre-aggregated marts, no sampling knob needed there)

`models/congestion/build_features.py::load_raw_trips()` already pushes
`USING SAMPLE N ROWS (reservoir, seed)` down into DuckDB — never
`pd.read_parquet().sample()` — so scaling up is just changing one number
and re-running, not new code.

1. Start at `SAMPLE_ROWS = 1_000_000`. Fast, cheap, good enough to catch
   bugs in the pipeline before spending a long GPU session on it.
2. Only go to `5_000_000`, then `10_000_000`, `25_000_000`, `50_000_000`,
   and finally `None` (`ALL`, ~113M rows) if the **held-out test metric**
   (RMSE/MAE for congestion, pinball loss + p10–p90 coverage for ETA)
   meaningfully improves at the previous step. If test RMSE barely moves
   between 5M and 10M, there is no reason to pay for 50M or ALL — this
   mirrors the repo's own rule against training on all 113M raw rows by
   default (`IMPLEMENTATION_AUDIT.md` section 11).
3. Notebook 01's cell 9 accumulates a small `run_log` table (rows / time /
   metrics) across every sample size actually run in the session — use it
   to decide where to stop, don't just run `ALL` because it's available.
