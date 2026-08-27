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
    args = parser.parse_args()
    main(sample_rows=args.sample_rows)
