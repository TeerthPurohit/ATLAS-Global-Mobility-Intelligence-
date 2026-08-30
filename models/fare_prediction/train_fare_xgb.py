"""Train a single tuned XGBoost fare-prediction model (SPEC-007).

Deliberately not a ladder (see spec NFR) — one XGBoost regressor, RMSE/MAE
reported honestly on a held-out block. No ladder, no LSTM variant.

Chronological split, block-gap aware (ADR-003 + EDA finding): the warehouse
only has trips for Jan/Mar/Jun 2024 — Feb/Apr/May are missing, so the data is
three disjoint monthly blocks, not one continuous timeline. A plain
row-count-fraction split across the concatenated blocks would land the test
cutoff partway into June (Jan+Mar is already ~67% of all rows), silently
mixing early-June "train" rows with late-June "test" rows from the same
block. Instead: train+val = Jan+Mar (the two earlier blocks), test = June in
full (the most recent complete block, held out entirely) — this is the
split ADR-003 intends: the model never sees anything from the test period,
directly or by proximity. Within Jan+Mar, the most recent 15% by pickup_at
is validation, so val still precedes test and train still precedes val.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.chronological_split import split_demand_blocks

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"
ARTIFACT_DIR = Path(__file__).resolve().parent

FEATURES = ["pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week", "trip_distance"]
CATEGORICAL = ["pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week"]
TARGET = "total_amount"
SEED = 42
# Optional row cap for a faster retrain on a lower-power machine (ponytail:
# a reservoir sample, not a date-range cutoff, so the chronological
# train/val/test split below still sees the full 2024-2026 date range in
# proportion -- only invoked via train_and_save(sample_rows=...), never
# silently on by default; the full-data path (None) is what every existing
# test/CI invocation still gets).
TRAINING_SAMPLE_ROWS: int | None = None


def load_data(db_path: Path = DEFAULT_DB_PATH, sample_rows: int | None = TRAINING_SAMPLE_ROWS) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        query = f"select {', '.join(FEATURES)}, {TARGET}, pickup_at from int_trips_enriched"
        if sample_rows is not None:
            # Reservoir sample (uniform across the whole table, so the
            # chronological split downstream still spans the real date
            # range in proportion) with a fixed seed for reproducibility.
            query += f" USING SAMPLE {sample_rows} ROWS (reservoir, {SEED})"
        df = con.execute(query).fetchdf()
    finally:
        con.close()
    for col in CATEGORICAL:
        df[col] = df[col].astype("category")
    return df


def split_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Delegates entirely to the shared, gap-aware splitter (Phase 2 dedup --
    # this used to carry its own byte-for-byte copy of this logic).
    return split_demand_blocks(df, "pickup_at")


def rmse_mae(y_true, y_pred) -> tuple[float, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    return rmse, mae


def tune(train: pd.DataFrame, val: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Small manual grid, selected by validation RMSE. Not a full ladder or
    CV search (out of scope per spec) — just enough to call this "tuned"
    honestly, with every candidate's result recorded for the artifact."""
    grid = [
        {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 300},
        {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300},
        {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 500},
        {"max_depth": 8, "learning_rate": 0.1, "n_estimators": 300},
    ]
    results = []
    best = None
    for params in grid:
        model = xgb.XGBRegressor(
            **params, tree_method="hist", enable_categorical=True, random_state=SEED, n_jobs=-1
        )
        model.fit(train[FEATURES], train[TARGET])
        rmse, mae = rmse_mae(val[TARGET], model.predict(val[FEATURES]))
        result = {**params, "val_rmse": rmse, "val_mae": mae}
        results.append(result)
        if best is None or rmse < best["val_rmse"]:
            best = result
    return best, results


GRID = [
    {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300},
    {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 500},
    {"max_depth": 8, "learning_rate": 0.1, "n_estimators": 300},
]
DEFAULT_BATCH_ROWS = 2_000_000
CHECKPOINT_PATH = ARTIFACT_DIR / "_streaming_checkpoint.json"
# Fixed category domains -- the canonical NYC TLC zone ID range (1-265, from
# taxi_zone_lookup) and the fixed hour-of-day/day-of-week ranges. Streaming
# the raw table in batches and calling pandas' plain `.astype("category")`
# per batch would infer categories from whatever's PRESENT IN THAT BATCH
# ALONE -- different batches would then encode the same zone ID to different
# integer codes, which xgb.DMatrix built from an iterator has no way to
# detect or warn about. That's a silent-wrong-number bug, not a crash, so
# every batch must be cast against this same fixed domain instead.
CATEGORICAL_DOMAINS: dict[str, list[int]] = {
    "pickup_location_id": list(range(1, 266)),
    "dropoff_location_id": list(range(1, 266)),
    "pickup_hour": list(range(24)),
    "pickup_day_of_week": list(range(7)),
}


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _apply_categorical_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col, domain in CATEGORICAL_DOMAINS.items():
        df[col] = pd.Categorical(df[col], categories=domain)
    return df


def compute_split_bounds(con: duckdb.DuckDBPyConnection) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    ts_df = con.execute("select pickup_at from int_trips_enriched").df()
    train, val, test = split_demand_blocks(ts_df, "pickup_at")
    assert train["pickup_at"].max() < val["pickup_at"].min() < test["pickup_at"].min(), "chronological split leaked"
    return train["pickup_at"].max(), val["pickup_at"].min(), test["pickup_at"].min()


def _where_for(split: str, bounds: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]) -> str:
    train_end, val_start, test_start = bounds
    if split == "train":
        return f"pickup_at <= '{train_end}'"
    if split == "val":
        return f"pickup_at >= '{val_start}' and pickup_at < '{test_start}'"
    if split == "train_val":
        return f"pickup_at < '{test_start}'"
    if split == "test":
        return f"pickup_at >= '{test_start}'"
    raise ValueError(f"unknown split={split!r}")


def stream_raw_batches(con: duckdb.DuckDBPyConnection, where: str, batch_rows: int = DEFAULT_BATCH_ROWS):
    query = f"select {', '.join(FEATURES)}, {TARGET}, pickup_at from int_trips_enriched where {where}"
    result = con.execute(query)
    reader = result.to_arrow_reader(batch_rows) if hasattr(result, "to_arrow_reader") else result.fetch_record_batch(batch_rows)
    for record_batch in reader:
        yield _apply_categorical_dtypes(record_batch.to_pandas())


def materialize_split(
    con: duckdb.DuckDBPyConnection, split: str, bounds: tuple, batch_rows: int = DEFAULT_BATCH_ROWS
) -> pd.DataFrame:
    parts = list(stream_raw_batches(con, _where_for(split, bounds), batch_rows))
    if not parts:
        return pd.DataFrame(columns=[*FEATURES, TARGET, "pickup_at"])
    return pd.concat(parts, ignore_index=True)


class TrainDataIter(xgb.DataIter):
    """At most `batch_rows` (default 2M) feature rows ever in memory at
    once -- same external-memory shape `congestion/streaming_features.py`
    and `eta/train_quantile_eta.py` already use for this warehouse."""

    def __init__(self, con: duckdb.DuckDBPyConnection, bounds: tuple, split: str = "train", batch_rows: int = DEFAULT_BATCH_ROWS) -> None:
        self._con = con
        self._where = _where_for(split, bounds)
        self._batch_rows = batch_rows
        self._reader_iter = None
        super().__init__()

    def reset(self) -> None:
        self._reader_iter = stream_raw_batches(self._con, self._where, self._batch_rows)

    def next(self, input_data) -> int:
        if self._reader_iter is None:
            self.reset()
        try:
            batch = next(self._reader_iter)
        except StopIteration:
            return 0
        input_data(data=batch[FEATURES], label=batch[TARGET])
        return 1


def _load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"grid_results": [], "final_model": None}


def _save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


def _tune_streaming(con, bounds, state: dict, device: str) -> tuple[dict, list[dict], pd.DataFrame]:
    _log("materializing val split")
    val_df = materialize_split(con, "val", bounds)
    _log(f"val split ready: {len(val_df)} rows")

    done_by_params = {json.dumps(r["params"], sort_keys=True): r for r in state["grid_results"]}
    results = []
    best = None
    for i, params in enumerate(GRID, 1):
        key = json.dumps(params, sort_keys=True)
        if key in done_by_params:
            result = done_by_params[key]["result"]
            _log(f"grid candidate {i}/{len(GRID)} {params} -- resumed from checkpoint, val_rmse={result['val_rmse']:.4f}")
        else:
            _log(f"grid candidate {i}/{len(GRID)} {params} -- training on {device}")
            t0 = time.perf_counter()
            it = TrainDataIter(con, bounds, split="train")
            dtrain = xgb.DMatrix(it, enable_categorical=True)
            xgb_params = {
                "tree_method": "hist", "device": device, "seed": SEED,
                "max_depth": params["max_depth"], "learning_rate": params["learning_rate"],
            }
            booster = xgb.train(xgb_params, dtrain, num_boost_round=params["n_estimators"])
            preds = booster.predict(xgb.DMatrix(val_df[FEATURES], enable_categorical=True))
            rmse, mae = rmse_mae(val_df[TARGET], preds)
            result = {**params, "val_rmse": rmse, "val_mae": mae}
            _log(f"grid candidate {i}/{len(GRID)} done in {time.perf_counter()-t0:.1f}s: val_rmse={rmse:.4f} val_mae={mae:.4f}")
            state["grid_results"].append({"params": params, "result": result})
            _save_checkpoint(state)
        results.append(result)
        if best is None or result["val_rmse"] < best["val_rmse"]:
            best = result
    return best, results, val_df


def train_and_save_streaming(device: str = "cpu", db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Full-warehouse fare training via external-memory streaming (same
    shape as congestion/ETA's streaming paths) -- brings the model current
    against the whole ~113M-row corpus instead of the stale 3-month
    snapshot `main(sample_rows=...)`'s plain in-memory `load_data()` was
    limited to, and lets it run on GPU (`device="cuda"`)."""
    _log("connecting to warehouse")
    con = duckdb.connect(str(db_path), read_only=True)
    state = _load_checkpoint()
    if state["grid_results"] or state["final_model"]:
        _log(f"resuming from checkpoint: {len(state['grid_results'])} grid candidate(s), final_model={'saved' if state['final_model'] else 'not yet'}")

    _log("computing split bounds")
    t0 = time.perf_counter()
    bounds = compute_split_bounds(con)
    train_end, val_start, test_start = bounds
    _log(f"bounds ready in {time.perf_counter()-t0:.1f}s: train_end={train_end} val_start={val_start} test_start={test_start}")

    best, grid_results, val_df = _tune_streaming(con, bounds, state, device)
    final_params = {k: best[k] for k in ("max_depth", "learning_rate", "n_estimators")}
    _log(f"grid search complete, best={final_params}")

    model_path = ARTIFACT_DIR / "fare_xgb_model.json"
    if state["final_model"] == final_params and model_path.exists():
        _log("final refit already done for these hyperparameters -- loading saved model instead of retraining")
        booster = xgb.Booster()
        booster.load_model(str(model_path))
    else:
        _log(f"training final refit on train+val ({device})")
        t0 = time.perf_counter()
        it = TrainDataIter(con, bounds, split="train_val")
        dtrain_val = xgb.DMatrix(it, enable_categorical=True)
        xgb_params = {
            "tree_method": "hist", "device": device, "seed": SEED,
            "max_depth": final_params["max_depth"], "learning_rate": final_params["learning_rate"],
        }
        booster = xgb.train(xgb_params, dtrain_val, num_boost_round=final_params["n_estimators"])
        _log(f"final refit done in {time.perf_counter()-t0:.1f}s")
        booster.save_model(str(model_path))  # save before the (cheaper) test-eval step, same reasoning as congestion/ETA
        state["final_model"] = final_params
        _save_checkpoint(state)
        _log("model saved")

    _log("materializing test split + scoring")
    t0 = time.perf_counter()
    test_df = materialize_split(con, "test", bounds)
    preds = booster.predict(xgb.DMatrix(test_df[FEATURES], enable_categorical=True))
    test_rmse, test_mae = rmse_mae(test_df[TARGET], preds)
    _log(f"test scoring done in {time.perf_counter()-t0:.1f}s: test_rmse={test_rmse:.4f} test_mae={test_mae:.4f}")

    metadata = {
        "seed": SEED, "training_sample_rows": None, "training_mode": f"streaming_external_memory_{device}",
        "date_range": {
            "train": ["(streamed, not materialized)", str(train_end)],
            "val": [str(val_start), str(test_start)],
            "test": [str(test_start), "(latest)"],
        },
        "n_rows": {"val": len(val_df), "test": len(test_df)},
        "features": FEATURES, "categorical_features": CATEGORICAL, "target": TARGET,
        "hyperparameters": {**final_params, "device": device},
        "hyperparameter_search": grid_results,
        "metrics": {
            "val_rmse": best["val_rmse"], "val_mae": best["val_mae"],
            "test_rmse": test_rmse, "test_mae": test_mae,
        },
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "fare_xgb_metadata.json").write_text(json.dumps(metadata, indent=2))
    CHECKPOINT_PATH.unlink(missing_ok=True)
    _log("fare training complete")
    return metadata


def main(sample_rows: int | None = TRAINING_SAMPLE_ROWS) -> None:
    df = load_data(sample_rows=sample_rows)
    train, val, test = split_data(df)
    assert train["pickup_at"].max() < val["pickup_at"].min(), "train must precede val"
    assert val["pickup_at"].max() < test["pickup_at"].min(), "val must precede test"

    best, grid_results = tune(train, val)
    final_params = {k: best[k] for k in ("max_depth", "learning_rate", "n_estimators")}

    # Refit on train+val with the winning hyperparameters; test is touched
    # exactly once, here.
    train_val = pd.concat([train, val])
    model = xgb.XGBRegressor(
        **final_params, tree_method="hist", enable_categorical=True, random_state=SEED, n_jobs=-1
    )
    model.fit(train_val[FEATURES], train_val[TARGET])
    test_rmse, test_mae = rmse_mae(test[TARGET], model.predict(test[FEATURES]))

    model.save_model(str(ARTIFACT_DIR / "fare_xgb_model.json"))
    metadata = {
        "seed": SEED,
        "training_sample_rows": sample_rows,
        "date_range": {
            "train": [str(train["pickup_at"].min()), str(train["pickup_at"].max())],
            "val": [str(val["pickup_at"].min()), str(val["pickup_at"].max())],
            "test": [str(test["pickup_at"].min()), str(test["pickup_at"].max())],
        },
        "n_rows": {"train": len(train), "val": len(val), "test": len(test)},
        "features": FEATURES,
        "categorical_features": CATEGORICAL,
        "target": TARGET,
        "hyperparameters": final_params,
        "hyperparameter_search": grid_results,
        "metrics": {
            "val_rmse": best["val_rmse"],
            "val_mae": best["val_mae"],
            "test_rmse": test_rmse,
            "test_mae": test_mae,
        },
        "library_versions": {
            "xgboost": xgb.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    (ARTIFACT_DIR / "fare_xgb_metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"chosen hyperparameters: {final_params}")
    print(f"val  RMSE={best['val_rmse']:.3f}  MAE={best['val_mae']:.3f}")
    print(f"test RMSE={test_rmse:.3f}  MAE={test_mae:.3f}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-rows", type=int, default=TRAINING_SAMPLE_ROWS)
    parser.add_argument("--streaming", action="store_true", help="train on the full warehouse via external-memory streaming instead of --sample-rows in-memory")
    parser.add_argument("--device", default="cpu", help="'cpu' or 'cuda' -- only used with --streaming")
    args = parser.parse_args()
    if args.streaming:
        meta = train_and_save_streaming(device=args.device)
        print(f"chosen hyperparameters: {meta['hyperparameters']}")
        print(f"val  RMSE={meta['metrics']['val_rmse']:.3f}  MAE={meta['metrics']['val_mae']:.3f}")
        print(f"test RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
    else:
        main(sample_rows=args.sample_rows)
