"""External-memory training path for the congestion/ETA feature table, used
when `sample_rows=None` (train on the full ~113M-row corpus, project
decision 2026-08-28 -- see models/notebooks/README.md's progressive-sampling
section). `build_features()`'s ordinary in-memory path materializes the
whole feature table in pandas at once, which OOMs even on free-tier Colab
(~12GB RAM) at this scale -- confirmed empirically, not a theoretical
concern (crashed partway through a congestion grid candidate's boosting
rounds, 2026-08-28).

This module streams `int_trips_enriched` from DuckDB in batches
(`fetch_record_batch`), applies `build_features.py`'s existing
`transform_batch()` -- the SAME transform the small-sample path uses, not a
reimplementation -- per batch, and feeds XGBoost's external-memory
`xgb.DataIter` interface. At most one batch's worth of feature rows is ever
held in memory at once for `train`.

Only `train` is streamed this way (~78M of ~113M rows on the current
warehouse -- the dominant memory cost). `val`/`test` (~14M/~21M rows) are
read via the same batched reader but concatenated into one in-memory
DataFrame, since their size is small enough to score directly without
external-memory predict (ponytail: a real corner cut, not free -- if
val/test ever grow enough to OOM too, `TrainDataIter`'s pattern generalizes
to them, just with `booster.predict()` called per-batch via `xgb.DMatrix`
instead of once on the whole frame).
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_features import (
    _RAW_TRIPS_WHERE,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    load_lookups,
    transform_batch,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.chronological_split import split_demand_blocks

DEFAULT_BATCH_ROWS = 2_000_000
Lookups = tuple[pd.DataFrame, dict[str, int], pd.DataFrame]
Bounds = tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]


def compute_split_bounds(con: duckdb.DuckDBPyConnection) -> Bounds:
    """(train_end, val_start, test_start): the same three boundaries
    `split_demand_blocks()` produces over the full feature table, derived
    cheaply from just the `pickup_at` column (one column across ~113M rows,
    not the full joined feature table this whole module exists to avoid
    materializing) -- reuses `split_demand_blocks()` unchanged so the
    boundaries are exactly what the small-sample in-memory path would
    compute, not a reimplementation that could silently drift from it."""
    ts_df = con.execute(f"select pickup_at from int_trips_enriched where {_RAW_TRIPS_WHERE}").df()
    train, val, test = split_demand_blocks(ts_df, "pickup_at")
    assert train["pickup_at"].max() < val["pickup_at"].min() < test["pickup_at"].min(), "chronological split leaked"
    return train["pickup_at"].max(), val["pickup_at"].min(), test["pickup_at"].min()


def _where_for(split: str, bounds: Bounds) -> str:
    train_end, val_start, test_start = bounds
    if split == "train":
        return f"{_RAW_TRIPS_WHERE} and pickup_at <= '{train_end}'"
    if split == "val":
        return f"{_RAW_TRIPS_WHERE} and pickup_at >= '{val_start}' and pickup_at < '{test_start}'"
    if split == "train_val":
        # train + val combined: everything before the held-out test block --
        # used for the final refit-on-train+val step every model in this
        # repo does once grid search picks a winning hyperparameter set.
        return f"{_RAW_TRIPS_WHERE} and pickup_at < '{test_start}'"
    if split == "test":
        return f"{_RAW_TRIPS_WHERE} and pickup_at >= '{test_start}'"
    raise ValueError(f"unknown split={split!r}")


def stream_raw_batches(
    con: duckdb.DuckDBPyConnection, where: str, batch_rows: int = DEFAULT_BATCH_ROWS
) -> Iterator[pd.DataFrame]:
    query = (
        "select pickup_at, pickup_hour, pickup_day_of_week, pickup_date, pickup_location_id, "
        f"trip_distance, trip_duration_minutes from int_trips_enriched where {where}"
    )
    reader = con.execute(query).to_arrow_reader(batch_rows)
    for record_batch in reader:
        batch = record_batch.to_pandas()
        # Arrow's to_pandas() gives pickup_date as object/datetime.date;
        # .fetchdf() (used everywhere else -- weather_demand, holiday_flags
        # keys) gives datetime64[us] Timestamps. Left unmatched, this
        # wouldn't just break the weather_demand merge (loud) -- it would
        # silently NaN every is_holiday lookup too (.map() against
        # mismatched key types returns NaN, not an error).
        batch["pickup_date"] = pd.to_datetime(batch["pickup_date"])
        yield batch


def count_split(con: duckdb.DuckDBPyConnection, split: str, bounds: Bounds) -> int:
    """Cheap row count (a single aggregate scan, not a materialization) for
    metadata reporting -- so streamed splits still get a real `n_rows`
    number instead of a placeholder."""
    where = _where_for(split, bounds)
    return con.execute(f"select count(*) from int_trips_enriched where {where}").fetchone()[0]


def materialize_split(
    con: duckdb.DuckDBPyConnection, split: str, bounds: Bounds, lookups: Lookups,
    batch_rows: int = DEFAULT_BATCH_ROWS,
) -> pd.DataFrame:
    """val/test only -- see module docstring for why these two are
    materialized in memory (stream-read, then concatenated) rather than fed
    through `TrainDataIter`."""
    free_flow, holiday_flags, weather_demand = lookups
    where = _where_for(split, bounds)
    parts = [
        transform_batch(batch, free_flow, holiday_flags, weather_demand)
        for batch in stream_raw_batches(con, where, batch_rows)
    ]
    if not parts:
        return pd.DataFrame(columns=[*FEATURE_COLUMNS, TARGET_COLUMN, "pickup_at"])
    return pd.concat(parts, ignore_index=True)


class TrainDataIter(xgb.DataIter):
    """Feeds XGBoost's external-memory training one transformed batch at a
    time -- at most `batch_rows` (default 2M) feature rows are ever in
    memory at once, never the full ~78M-row train split. `cache_prefix`
    points XGBoost at on-disk paging for processed batches instead of
    holding them all in RAM, which is what actually avoids the OOM."""

    def __init__(
        self, con: duckdb.DuckDBPyConnection, bounds: Bounds, lookups: Lookups,
        batch_rows: int = DEFAULT_BATCH_ROWS, split: str = "train",
    ) -> None:
        self._con = con
        self._where = _where_for(split, bounds)
        self._free_flow, self._holiday_flags, self._weather_demand = lookups
        self._batch_rows = batch_rows
        self._reader_iter: Iterator[pd.DataFrame] | None = None
        self._cache_dir = tempfile.mkdtemp(prefix="xgb_ext_mem_")
        super().__init__(cache_prefix=os.path.join(self._cache_dir, "cache"))

    def reset(self) -> None:
        self._reader_iter = stream_raw_batches(self._con, self._where, self._batch_rows)

    def next(self, input_data) -> int:
        if self._reader_iter is None:
            self.reset()
        try:
            raw_batch = next(self._reader_iter)
        except StopIteration:
            return 0
        features = transform_batch(raw_batch, self._free_flow, self._holiday_flags, self._weather_demand)
        if len(features) == 0:
            return self.next(input_data)  # an all-filtered-out batch is not "no more data"
        input_data(data=features[FEATURE_COLUMNS], label=features[TARGET_COLUMN])
        return 1


def load_streaming_context(con: duckdb.DuckDBPyConnection) -> tuple[Bounds, Lookups]:
    """One call to get everything the streaming path needs before touching
    any big-table row data: split boundaries (single-column scan) + the
    three small lookup tables `load_lookups()` already computes cheaply."""
    return compute_split_bounds(con), load_lookups(con)
