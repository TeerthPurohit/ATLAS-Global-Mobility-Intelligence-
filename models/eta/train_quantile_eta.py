"""Quantile ETA models (Phase 7): eta_p10/p50/p90 via XGBoost's native
`reg:quantileerror` objective (pinball loss), one model per quantile
(xgboost>=2.0 supports `quantile_alpha` directly -- no need for 3 separate
architectures or a custom loss).

Target is the trip's actual observed duration (`trip_duration_minutes`),
same feature table as the Phase 6 congestion model
(`models/congestion/build_features.py` -- reused, not duplicated). These
quantile models are a direct empirical fit to observed duration; they are
NOT the production ETA path (see `compose_eta.py` for the explicit
T_freeflow * congestion_multiplier composition the spec asks for) -- they
exist to measure real prediction-interval coverage on held-out data.

Coverage is *measured*, not assumed: fraction of held-out test rows where
p10_pred <= actual <= p90_pred, reported honestly even if it misses the
nominal 80%.

`sample_rows=None` (train on the full ~113M-row corpus, project decision
2026-08-28) routes to `models/congestion/streaming_features.py`'s
external-memory path -- same reasoning as
`models/congestion/train_congestion_xgb.py`'s identical dispatch; the two
share this feature table and the OOM risk is the same.
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
from sklearn.metrics import mean_absolute_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from congestion.build_features import _RAW_TRIPS_WHERE, DEFAULT_DB_PATH, FEATURE_COLUMNS, build_features, transform_batch
from congestion.streaming_features import (
    DEFAULT_BATCH_ROWS,
    TrainDataIter,
    count_split,
    load_streaming_context,
    materialize_split,
)
from data_prep.chronological_split import split_demand_blocks

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42
TARGET_COLUMN = "trip_duration_minutes"
QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}
XGB_PARAMS = {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 300}
CHECKPOINT_PATH = ARTIFACT_DIR / "_streaming_checkpoint.json"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load_checkpoint() -> dict:
    """Resume state keyed on this run's own XGB_PARAMS -- NOT on whether
    eta_{name}_model.json merely exists. Bare file-existence was a real bug:
    tests/test_quantile_eta_ordering_and_coverage.py calls this module's
    non-streaming train_and_save() with a 20K-row sample df, which writes to
    these exact same production paths. A streaming run that resumed off
    file-existence alone silently scored a 20K-row-trained model against the
    real ~21M-row test set and reported that as the full-data result
    (caught 2026-08-28 by checking the log for "resuming from saved" against
    a run that should have been training fresh)."""
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"done": {}}  # name -> XGB_PARAMS it was actually trained with


def _save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


class _ProgressCallback(xgb.callback.TrainingCallback):
    """Prints a timestamped line every `every` boosting rounds -- without
    this, a multi-hour CPU `xgb.train()` call for ~90M rows produces zero
    output between "training" and "trained in Xs", which is bad for anyone
    monitoring a long-running background job. `start_round` offsets the
    reported round number when resuming from a mid-quantile checkpoint (see
    `_CheckpointCallback`), so logs show the true absolute round out of 300,
    not a count restarted at 0."""

    def __init__(self, name: str, total_rounds: int, every: int = 25, start_round: int = 0) -> None:
        self.name = name
        self.total_rounds = total_rounds
        self.every = every
        self.start_round = start_round
        self._t0 = time.perf_counter()

    def after_iteration(self, model, epoch: int, evals_log: dict) -> bool:
        round_num = self.start_round + epoch + 1
        if round_num % self.every == 0 or round_num == self.total_rounds:
            pct = 100 * round_num / self.total_rounds
            elapsed = time.perf_counter() - self._t0
            _log(f"quantile {self.name}: round {round_num}/{self.total_rounds} ({pct:.1f}%), elapsed {elapsed:.0f}s")
        return False  # False = keep training


class _CheckpointCallback(xgb.callback.TrainingCallback):
    """Saves the in-progress booster every `every` rounds so a crash mid-
    quantile (300 rounds can be a long CPU run) resumes from the last
    checkpoint instead of restarting that quantile from round 0 -- the
    existing checkpoint only covered whole-quantile granularity, which is a
    big unit of loss for a single multi-hour boosting call. Records the
    absolute round reached in the shared _streaming_checkpoint.json under
    "in_progress", keyed on XGB_PARAMS same as the per-quantile "done"
    entries, so a params change doesn't silently resume a stale partial."""

    def __init__(self, name: str, total_rounds: int, checkpoint_model_path: Path, start_round: int = 0, every: int = 50) -> None:
        self.name = name
        self.total_rounds = total_rounds
        self.checkpoint_model_path = checkpoint_model_path
        self.start_round = start_round
        self.every = every

    def after_iteration(self, model, epoch: int, evals_log: dict) -> bool:
        round_num = self.start_round + epoch + 1
        if round_num % self.every == 0 and round_num < self.total_rounds:
            model.save_model(str(self.checkpoint_model_path))
            state = _load_checkpoint()
            state["in_progress"] = {"name": self.name, "round": round_num, "params": XGB_PARAMS}
            _save_checkpoint(state)
            _log(f"quantile {self.name}: mid-training checkpoint saved at round {round_num}/{self.total_rounds}")
        return False  # False = keep training


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    diff = y_true - y_pred
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1) * diff)))


def train_quantile(train: pd.DataFrame, alpha: float) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor(
        **XGB_PARAMS,
        objective="reg:quantileerror",
        quantile_alpha=alpha,
        tree_method="hist",
        random_state=SEED,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN])
    return model


def _train_and_save_streaming(quantiles: dict[str, float] | None = None) -> dict:
    """`quantiles` restricts training to a subset of QUANTILES (e.g. {"p50": 0.5}
    on one machine while another machine handles the rest) -- for splitting the
    three independent quantile models across machines in parallel. Defaults to
    all three. The returned metadata only covers the quantiles actually run
    here; merging a full three-quantile eta_metadata.json is the caller's job
    once all machines' outputs are collected."""
    quantiles = quantiles if quantiles is not None else QUANTILES
    _log("connecting to warehouse")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    _log("computing split bounds + loading lookups")
    t0 = time.perf_counter()
    bounds, lookups = load_streaming_context(con)
    train_end, val_start, test_start = bounds
    _log(f"bounds/lookups ready in {time.perf_counter()-t0:.1f}s")

    _log("materializing test split")
    t0 = time.perf_counter()
    test_df = materialize_split(con, "test", bounds, lookups)
    _log(f"test split ready in {time.perf_counter()-t0:.1f}s: {len(test_df)} rows")

    state = _load_checkpoint()
    if state["done"]:
        _log(f"resuming from checkpoint: {sorted(state['done'])} already trained this run")

    preds = {}
    per_quantile_metrics = {}
    dtrain_val = None  # built once, lazily, and reused across quantiles -- same train_val
    # rows/features for all three, so re-scanning the ~90M-row split per quantile was pure
    # waste. (A GPU miscalibration bug was briefly blamed on this reuse and disproven
    # 2026-08-29: rebuilding fresh per quantile produced byte-identical -- still broken --
    # results, so the bug was xgboost 3.2.0's reg:quantileerror + device=cuda on Kaggle,
    # not DMatrix sharing. Training now runs on CPU, where this is safe again.)
    for name, alpha in quantiles.items():
        model_path = ARTIFACT_DIR / f"eta_{name}_model.json"
        partial_path = ARTIFACT_DIR / f"_streaming_partial_{name}.json"
        booster = xgb.Booster()
        if state["done"].get(name) == XGB_PARAMS and model_path.exists():
            _log(f"quantile {name} (alpha={alpha}) -- resuming from checkpoint ({model_path.name})")
            booster.load_model(str(model_path))
        else:
            in_progress = state.get("in_progress")
            start_round = 0
            xgb_model_arg = None
            if (
                in_progress and in_progress.get("name") == name
                and in_progress.get("params") == XGB_PARAMS and partial_path.exists()
            ):
                start_round = in_progress["round"]
                xgb_model_arg = str(partial_path)
                _log(f"quantile {name} (alpha={alpha}) -- resuming mid-training from round {start_round}/{XGB_PARAMS['n_estimators']} ({partial_path.name})")
            else:
                _log(f"quantile {name} (alpha={alpha}) -- training")
            if dtrain_val is None:
                t0 = time.perf_counter()
                it = TrainDataIter(con, bounds, lookups, split="train_val", cache=False)
                dtrain_val = xgb.QuantileDMatrix(it)
                _log(f"train_val QuantileDMatrix materialized in {time.perf_counter()-t0:.1f}s (shared across remaining quantiles)")
            t0 = time.perf_counter()
            xgb_params = {
                **{k: v for k, v in XGB_PARAMS.items() if k != "n_estimators"},
                "objective": "reg:quantileerror", "quantile_alpha": alpha,
                "tree_method": "hist", "seed": SEED,
            }
            remaining_rounds = XGB_PARAMS["n_estimators"] - start_round
            booster = xgb.train(
                xgb_params, dtrain_val, num_boost_round=remaining_rounds, xgb_model=xgb_model_arg,
                callbacks=[
                    _ProgressCallback(name, XGB_PARAMS["n_estimators"], start_round=start_round),
                    _CheckpointCallback(name, XGB_PARAMS["n_estimators"], partial_path, start_round=start_round),
                ],
            )
            _log(f"quantile {name} trained in {time.perf_counter()-t0:.1f}s")
            # Save immediately, before scoring -- same reasoning as
            # congestion's identical fix: a multi-hour training step must
            # never be thrown away by a failure in the comparatively cheap
            # test-set prediction that follows.
            booster.save_model(str(model_path))
            partial_path.unlink(missing_ok=True)
            state.pop("in_progress", None)
            state["done"][name] = XGB_PARAMS
            _save_checkpoint(state)
            _log(f"quantile {name} model saved")

        p = booster.predict(xgb.DMatrix(test_df[FEATURE_COLUMNS]))
        preds[name] = p
        per_quantile_metrics[name] = {
            "alpha": alpha,
            "pinball_loss": pinball_loss(test_df[TARGET_COLUMN].to_numpy(), p, alpha),
            "mae": float(mean_absolute_error(test_df[TARGET_COLUMN], p)),
        }
        _log(f"quantile {name} scored: pinball_loss={per_quantile_metrics[name]['pinball_loss']:.4f}")

    # Coverage/ordering need all three quantiles' predictions -- null them out
    # when only a subset was trained here (e.g. one machine handling p50+p90
    # while another handles p10 in parallel); the caller merges partial runs
    # into a real three-quantile eta_metadata.json once everything's collected.
    have_all_three = {"p10", "p50", "p90"} <= preds.keys()
    if have_all_three:
        actual = test_df[TARGET_COLUMN].to_numpy()
        within_interval = (actual >= preds["p10"]) & (actual <= preds["p90"])
        coverage = float(np.mean(within_interval))
        ordering_violations = int(np.sum((preds["p10"] > preds["p50"]) | (preds["p50"] > preds["p90"])))
    else:
        coverage = None
        ordering_violations = None

    metadata = {
        "seed": SEED,
        "sample_rows": None,
        "training_mode": "streaming_external_memory",
        "date_range": {
            "train": ["(streamed, not materialized)", str(train_end)],
            "val": [str(val_start), str(test_start)],
            "test": [str(test_start), "(latest)"],
        },
        "n_rows": {"train_val_raw_upper_bound": count_split(con, "train_val", bounds), "test": len(test_df)},
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "hyperparameters": XGB_PARAMS,
        "quantiles": quantiles,
        "metrics": per_quantile_metrics,
        "prediction_interval_coverage": {
            "nominal": 0.80,
            "measured_p10_p90_coverage": coverage,
            "n_test_rows": int(len(test_df)),  # noqa: RUF046
            "note": (
                "empirically measured fraction of held-out test rows where actual duration fell within "
                "[p10_pred, p90_pred] -- not assumed or hardcoded; see the gap vs nominal 0.80 above"
            ),
        },
        "ordering_violations_p10_p50_p90": ordering_violations,
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "eta_metadata.json").write_text(json.dumps(metadata, indent=2))
    if have_all_three:
        CHECKPOINT_PATH.unlink(missing_ok=True)  # full success -- resume state no longer needed
    _log("eta training complete")
    return metadata


GPU_LADDER_RUNGS = [
    10_000_000, 20_000_000, 30_000_000, 40_000_000, 50_000_000, 60_000_000,
    70_000_000, 80_000_000, 90_000_000, 100_000_000, 110_000_000, 113_000_000,
]
GPU_COVERAGE_BREAK_THRESHOLD = 0.3  # nominal coverage is ~0.80; this low only happens via the known GPU quantileerror bug


def _stream_sampled_train_batches(con, sample_rows: int, test_start, batch_rows: int):
    """Same batched-Arrow-reader shape as `streaming_features.stream_raw_batches`,
    but a `sample_rows`-row reservoir sample of the train_val period (before
    `test_start`) instead of the whole period -- so the ladder can scale row
    count with the SAME chunked, external-memory construction production's
    full run uses (`TrainDataIter` + `QuantileDMatrix(iterator)`), instead of
    switching to a different, un-validated in-memory code path per rung. This
    also directly tests whether that streaming+GPU combination -- what the
    original broken 92M-row run actually used -- is itself implicated,
    independent of raw row count (see project memory
    `project_eta_gpu_only_decision_2026_08_30.md`)."""
    query = (
        "select pickup_at, pickup_hour, pickup_day_of_week, pickup_date, pickup_location_id, "
        f"trip_distance, trip_duration_minutes from int_trips_enriched where {_RAW_TRIPS_WHERE} "
        f"and pickup_at < '{test_start}' USING SAMPLE {sample_rows} ROWS (reservoir, {SEED})"
    )
    result = con.execute(query)
    reader = result.to_arrow_reader(batch_rows) if hasattr(result, "to_arrow_reader") else result.fetch_record_batch(batch_rows)
    for record_batch in reader:
        batch = record_batch.to_pandas()
        batch["pickup_date"] = pd.to_datetime(batch["pickup_date"])
        yield batch


class _SampledTrainDataIter(xgb.DataIter):
    """`TrainDataIter`'s sampled-to-a-fixed-row-count sibling for the GPU
    ladder -- at most `batch_rows` feature rows are ever held in memory at
    once, same external-memory shape production uses, just capped to
    `sample_rows` via reservoir sampling instead of taking the whole
    train_val period."""

    def __init__(self, con, sample_rows: int, test_start, lookups, batch_rows: int = DEFAULT_BATCH_ROWS) -> None:
        self._con = con
        self._sample_rows = sample_rows
        self._test_start = test_start
        self._free_flow, self._holiday_flags, self._weather_demand = lookups
        self._batch_rows = batch_rows
        self._reader_iter = None
        super().__init__()  # no cache_prefix -- QuantileDMatrix requires cache=False, same as TrainDataIter(cache=False)

    def reset(self) -> None:
        self._reader_iter = _stream_sampled_train_batches(self._con, self._sample_rows, self._test_start, self._batch_rows)

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


def _train_quantiles_streaming(
    con, sample_rows: int, test_start, lookups, dtest: xgb.DMatrix, actual: np.ndarray,
    num_boost_round: int, device: str, batch_rows: int,
) -> tuple[dict[str, xgb.Booster], dict[str, dict], float]:
    """One rung's worth of training (all three quantiles) via the streamed,
    row-count-capped `_SampledTrainDataIter` -> boosters + per-quantile
    metrics + measured coverage against the shared, fixed `dtest`/`actual`."""
    it = _SampledTrainDataIter(con, sample_rows, test_start, lookups, batch_rows)
    dtrain = xgb.QuantileDMatrix(it)
    boosters: dict[str, xgb.Booster] = {}
    metrics: dict[str, dict] = {}
    for name, alpha in QUANTILES.items():
        params = {
            "max_depth": XGB_PARAMS["max_depth"], "learning_rate": XGB_PARAMS["learning_rate"],
            "objective": "reg:quantileerror", "quantile_alpha": alpha,
            "tree_method": "hist", "device": device, "seed": SEED,
        }
        booster = xgb.train(params, dtrain, num_boost_round=num_boost_round)
        pred = booster.predict(dtest)
        boosters[name] = booster
        metrics[name] = {"alpha": alpha, "mae": float(mean_absolute_error(actual, pred)), "pred": pred}
    coverage = float(np.mean((actual >= metrics["p10"]["pred"]) & (actual <= metrics["p90"]["pred"])))
    return boosters, metrics, coverage


def train_gpu_row_ladder(
    rungs: list[int] = GPU_LADDER_RUNGS, probe_rounds: int = 100, final_rounds: int = 300,
    device: str = "cuda", output_dir: Path = ARTIFACT_DIR, batch_rows: int = DEFAULT_BATCH_ROWS,
) -> dict:
    """Diagnostic + production in one pass: trains quantile models at
    increasing row counts (cheap `probe_rounds` each) to find where
    `reg:quantileerror` + `device="cuda"` breaks -- measured coverage
    collapses from ~0.80 to near-zero above some row count between 10.25M
    (confirmed correct) and 92M (confirmed broken), see project memory
    `project_eta_gpu_only_decision_2026_08_30.md`. Each rung streams its
    sampled train_val rows in `batch_rows`-sized chunks (external-memory,
    same as production's full run) instead of materializing the whole rung
    in pandas at once -- an earlier in-memory version of this ladder OOM'd
    at 40M rows on Kaggle. Stops at the first broken rung or hard failure,
    then retrains the LAST safe rung at full `final_rounds` and saves it as
    the real production eta_p10/p50/p90_model.json."""
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    bounds, lookups = load_streaming_context(con)
    _, _, test_start = bounds
    _log("materializing fixed test split (same for every rung)")
    t0 = time.perf_counter()
    test_df = materialize_split(con, "test", bounds, lookups, batch_rows=batch_rows)
    _log(f"test split ready in {time.perf_counter()-t0:.1f}s: {len(test_df)} rows")
    dtest = xgb.DMatrix(test_df[FEATURE_COLUMNS])
    actual = test_df[TARGET_COLUMN].to_numpy()

    ladder_results = []
    last_safe_rung = None
    for rung in rungs:
        _log(f"ladder rung {rung:,} rows -- streaming + training on GPU")
        try:
            t0 = time.perf_counter()
            _, metrics, coverage = _train_quantiles_streaming(
                con, rung, test_start, lookups, dtest, actual, probe_rounds, device, batch_rows
            )
            elapsed = time.perf_counter() - t0
            row = {
                "rung_requested": rung, "mae": {k: v["mae"] for k, v in metrics.items()},
                "coverage": coverage, "elapsed_s": round(elapsed, 1),
            }
            ladder_results.append(row)
            _log(f"ladder rung {rung:,}: coverage={coverage:.4f} mae={row['mae']} ({elapsed:.0f}s)")
            if coverage < GPU_COVERAGE_BREAK_THRESHOLD:
                _log(f"ladder rung {rung:,}: BROKEN (coverage {coverage:.4f} << nominal 0.80) -- stopping ladder here")
                break
            last_safe_rung = rung
        except Exception as exc:  # noqa: BLE001 -- one bad rung (OOM, CUDA error) must not kill the whole ladder silently
            _log(f"ladder rung {rung:,}: FAILED with {type(exc).__name__}: {exc}")
            ladder_results.append({"rung_requested": rung, "error": f"{type(exc).__name__}: {exc}"})
            break

    result = {"ladder": ladder_results, "last_safe_rung": last_safe_rung, "device": device, "n_test_rows": len(test_df)}
    (output_dir / "eta_gpu_ladder_report.json").write_text(json.dumps(result, indent=2))
    if last_safe_rung is None:
        _log("no rung trained successfully -- nothing to save")
        return result

    _log(f"retraining production models at last safe rung {last_safe_rung:,} rows, {final_rounds} rounds")
    boosters, metrics, coverage = _train_quantiles_streaming(
        con, last_safe_rung, test_start, lookups, dtest, actual, final_rounds, device, batch_rows
    )
    for name, booster in boosters.items():
        booster.save_model(str(output_dir / f"eta_{name}_model.json"))
    ordering_violations = int(np.sum(
        (metrics["p10"]["pred"] > metrics["p50"]["pred"]) | (metrics["p50"]["pred"] > metrics["p90"]["pred"])
    ))
    metadata = {
        "seed": SEED, "sample_rows": last_safe_rung, "training_mode": f"gpu_ladder_streaming_{device}",
        "n_rows": {"train_val_requested": last_safe_rung, "test": len(test_df)},
        "features": FEATURE_COLUMNS, "target": TARGET_COLUMN,
        "hyperparameters": {**XGB_PARAMS, "n_estimators": final_rounds, "device": device},
        "quantiles": QUANTILES,
        "metrics": {k: {"alpha": v["alpha"], "mae": v["mae"]} for k, v in metrics.items()},
        "prediction_interval_coverage": {
            "nominal": 0.80, "measured_p10_p90_coverage": coverage, "n_test_rows": int(len(test_df)),  # noqa: RUF046
            "note": (
                "measured on the last GPU-ladder rung confirmed not broken -- see "
                "eta_gpu_ladder_report.json for the full rung-by-rung scan"
            ),
        },
        "ordering_violations_p10_p50_p90": ordering_violations,
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (output_dir / "eta_metadata.json").write_text(json.dumps(metadata, indent=2))
    _log(f"gpu ladder complete: last safe rung {last_safe_rung:,}, coverage {coverage:.4f}")
    return metadata


def train_and_save(
    df: pd.DataFrame | None = None, sample_rows: int | None = 300_000, output_dir: Path = ARTIFACT_DIR,
    quantiles: dict[str, float] | None = None,
) -> dict:
    if df is None and sample_rows is None:
        return _train_and_save_streaming(quantiles=quantiles)

    if df is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        df = build_features(con, sample_rows=sample_rows)
    else:
        sample_rows = "provided_externally"  # honesty: don't claim the default 300k when a caller (e.g. a test) passed its own df

    train, val, test = split_demand_blocks(df, "pickup_at")
    assert train["pickup_at"].max() < val["pickup_at"].min() < test["pickup_at"].min(), "chronological split leaked"
    train_val = pd.concat([train, val])

    preds = {}
    per_quantile_metrics = {}
    for name, alpha in QUANTILES.items():
        model = train_quantile(train_val, alpha)
        model.save_model(str(output_dir / f"eta_{name}_model.json"))
        p = model.predict(test[FEATURE_COLUMNS])
        preds[name] = p
        per_quantile_metrics[name] = {
            "alpha": alpha,
            "pinball_loss": pinball_loss(test[TARGET_COLUMN].to_numpy(), p, alpha),
            "mae": float(mean_absolute_error(test[TARGET_COLUMN], p)),
        }

    actual = test[TARGET_COLUMN].to_numpy()
    within_interval = (actual >= preds["p10"]) & (actual <= preds["p90"])
    coverage = float(np.mean(within_interval))
    ordering_violations = int(np.sum((preds["p10"] > preds["p50"]) | (preds["p50"] > preds["p90"])))

    metadata = {
        "seed": SEED,
        "sample_rows": sample_rows,
        "training_mode": "in_memory",
        "date_range": {
            "train": [str(train["pickup_at"].min()), str(train["pickup_at"].max())],
            "val": [str(val["pickup_at"].min()), str(val["pickup_at"].max())],
            "test": [str(test["pickup_at"].min()), str(test["pickup_at"].max())],
        },
        "n_rows": {"train": len(train), "val": len(val), "test": len(test)},
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "hyperparameters": XGB_PARAMS,
        "quantiles": QUANTILES,
        "metrics": per_quantile_metrics,
        "prediction_interval_coverage": {
            "nominal": 0.80,
            "measured_p10_p90_coverage": coverage,
            "n_test_rows": int(len(test)),  # noqa: RUF046
            "note": (
                "empirically measured fraction of held-out test rows where actual duration fell within "
                "[p10_pred, p90_pred] -- not assumed or hardcoded; see the gap vs nominal 0.80 above"
            ),
        },
        "ordering_violations_p10_p50_p90": ordering_violations,
        "library_versions": {"xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (output_dir / "eta_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    meta = train_and_save()
    print("pinball losses:", {k: round(v["pinball_loss"], 4) for k, v in meta["metrics"].items()})
    cov = meta["prediction_interval_coverage"]
    print(f"measured p10-p90 coverage: {cov['measured_p10_p90_coverage']:.4f} (nominal {cov['nominal']})")
    print(f"ordering violations (p10<=p50<=p90): {meta['ordering_violations_p10_p50_p90']}")
