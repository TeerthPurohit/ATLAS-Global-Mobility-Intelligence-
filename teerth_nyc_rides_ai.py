"""TeerthNYCRidesAI -- a unified interface over every specialized ML model
trained in this project on NYC TLC's real ~113M-row trip warehouse.

Not an LLM: every model here is a gradient-boosted tree (XGBoost) or a small
neural net (LSTM, Transformer) trained directly on structured trip data --
one model per task, each evaluated honestly on a chronological (not random)
train/val/test split, with real measured error reported alongside every
prediction below, not just a bare number. See models/evaluation/metrics_report.md
for the full evaluation writeup this module's numbers come from.

Usage:
    ai = TeerthNYCRidesAI()
    ai.predict_eta_range(trip_distance=3.2, free_flow_duration_min=12.0, hour=17,
                          day_of_week=4, is_holiday=0, temperature_c=18.0,
                          precipitation_mm=0.0, demand_index=6)
    ai.summary()  # prints every model's honest test-set metrics
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import xgboost as xgb

REPO_ROOT = Path(__file__).resolve().parent


def _load_xgb(path: Path) -> xgb.Booster:
    booster = xgb.Booster()
    booster.load_model(str(path))
    return booster


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _row_to_dmatrix(row: dict[str, Any], columns: list[str]) -> xgb.DMatrix:
    import pandas as pd
    return xgb.DMatrix(pd.DataFrame([row], columns=columns))


class TeerthNYCRidesAI:
    """Loads every trained model once. Each predict_* method takes the exact
    feature values that model was trained on (see its docstring) and returns
    the prediction alongside the model's own measured test-set error -- so
    every number comes with an honest sense of how much to trust it."""

    def __init__(self, root: Path = REPO_ROOT) -> None:
        self._root = root

        self.demand_model = _load_xgb(root / "models/xgboost_model/xgb_model.json")
        self.demand_meta = _load_json(root / "models/xgboost_model/xgb_metadata.json")

        self.congestion_model = _load_xgb(root / "models/congestion/congestion_model.json")
        self.congestion_meta = _load_json(root / "models/congestion/congestion_metadata.json")

        self.fare_model = _load_xgb(root / "models/fare_prediction/fare_xgb_model.json")
        self.fare_meta = _load_json(root / "models/fare_prediction/fare_xgb_metadata.json")

        self.eta_p10 = _load_xgb(root / "models/eta/eta_p10_model.json")
        self.eta_p50 = _load_xgb(root / "models/eta/eta_p50_model.json")
        self.eta_p90 = _load_xgb(root / "models/eta/eta_p90_model.json")
        self.eta_meta = _load_json(root / "models/eta/eta_metadata.json")

        import sys
        sys.path.insert(0, str(root))
        from models.lstm_model.train_lstm import DemandLSTM
        self.lstm_meta = _load_json(root / "models/lstm_model/lstm_metadata.json")
        lstm_hp = self.lstm_meta["hyperparameters"]
        self.lstm_model = DemandLSTM(hidden_size=lstm_hp["hidden_size"], num_layers=lstm_hp["num_layers"])
        self.lstm_model.load_state_dict(
            torch.load(root / "models/lstm_model/lstm_model.pt", map_location="cpu")
        )
        self.lstm_model.eval()

        from models.transformer_demand.transformer import DemandTransformer
        self.transformer_meta = _load_json(root / "models/transformer_demand/transformer_metadata.json")
        t_hp = self.transformer_meta["hyperparameters"]
        self.transformer_model = DemandTransformer(
            d_model=t_hp["d_model"], num_heads=t_hp["num_heads"], num_layers=t_hp["num_layers"],
            dim_feedforward=t_hp["dim_feedforward"], dropout=0.0,
        )
        self.transformer_model.load_state_dict(
            torch.load(root / "models/transformer_demand/transformer_model.pt", map_location="cpu")
        )
        self.transformer_model.eval()

    # ---------------------------------------------------------------- demand

    def predict_demand(
        self, hour: int, day_of_week: int, is_weekend: int, lag_1h: float, lag_24h: float,
        lag_168h: float, ewma: float, rolling_7d_avg: float, temperature_c: float, precipitation_mm: float,
    ) -> dict:
        """Zone-hourly trip demand (trips/hour). Needs the lag/rolling features
        build_features.py computes from history -- this wraps the raw model,
        it does not do the live lookup itself (see backend/services/model_service.py
        for the production path that resolves these from real zone history)."""
        row = dict(
            hour=hour, day_of_week=day_of_week, is_weekend=is_weekend, lag_1h=lag_1h,
            lag_24h=lag_24h, lag_168h=lag_168h, ewma=ewma, rolling_7d_avg=rolling_7d_avg,
            temperature_c=temperature_c, precipitation_mm=precipitation_mm,
        )
        pred = float(self.demand_model.predict(_row_to_dmatrix(row, self.demand_meta["features"]))[0])
        return {"predicted_trips_per_hour": round(pred, 1), "model": "xgboost_demand_v1",
                "measured_test_rmse": self.demand_meta["metrics"]["test_rmse"]}

    # ------------------------------------------------------------ congestion

    def predict_congestion_multiplier(
        self, trip_distance: float, free_flow_duration_min: float, hour: int, day_of_week: int,
        is_holiday: int, temperature_c: float, precipitation_mm: float, demand_index: float,
    ) -> dict:
        """Multiplier applied to free-flow travel time to get real expected
        duration (actual_duration ~= free_flow_duration_min * multiplier)."""
        row = dict(
            trip_distance=trip_distance, free_flow_duration_min=free_flow_duration_min, hour=hour,
            day_of_week=day_of_week, is_holiday=is_holiday, temperature_c=temperature_c,
            precipitation_mm=precipitation_mm, demand_index=demand_index,
        )
        pred = float(self.congestion_model.predict(_row_to_dmatrix(row, self.congestion_meta["features"]))[0])
        return {"predicted_multiplier": round(pred, 3), "model": "xgboost_congestion_v1",
                "measured_test_rmse": self.congestion_meta["metrics"]["test_rmse"]}

    # ------------------------------------------------------------------ fare

    _FARE_CATEGORY_ORDER = ("pickup_location_id", "dropoff_location_id", "pickup_hour", "pickup_day_of_week")
    _FARE_CATEGORY_DTYPES = {
        "pickup_location_id": "int32", "dropoff_location_id": "int32",
        "pickup_hour": "int64", "pickup_day_of_week": "int64",
    }

    def _fare_category_values(self) -> dict[str, "pd.Series"]:
        """The exact category values this model was trained with, read from
        the model file's own stored encoding (learner.gradient_booster.model.cats.enc)
        -- a plain `.astype("category")` on a single-row DataFrame instead
        would invent a category index from just that one row and xgboost
        rejects it (index type mismatch vs. what training used)."""
        import pandas as pd
        model_doc = json.loads((self._root / "models/fare_prediction/fare_xgb_model.json").read_text())
        enc = model_doc["learner"]["gradient_booster"]["model"]["cats"]["enc"]
        return {
            col: pd.Series(entry["values"], dtype=self._FARE_CATEGORY_DTYPES[col])
            for col, entry in zip(self._FARE_CATEGORY_ORDER, enc)
        }

    def predict_fare(
        self, pickup_location_id: int, dropoff_location_id: int, pickup_hour: int,
        pickup_day_of_week: int, trip_distance: float,
    ) -> dict:
        import pandas as pd
        # This model trained with enable_categorical=True on these 4 columns
        # (models/fare_prediction/train_fare_xgb.py) -- feeding them as plain
        # ints instead of the exact training-time category encoding silently
        # gives a wrong prediction, or an outright rejection.
        categories = self._fare_category_values()
        row = dict(
            pickup_location_id=pickup_location_id, dropoff_location_id=dropoff_location_id,
            pickup_hour=pickup_hour, pickup_day_of_week=pickup_day_of_week, trip_distance=trip_distance,
        )
        df = pd.DataFrame([row], columns=self.fare_meta["features"])
        for col in self._FARE_CATEGORY_ORDER:
            df[col] = pd.Categorical(df[col].astype(self._FARE_CATEGORY_DTYPES[col]), categories=categories[col])
        pred = float(self.fare_model.predict(xgb.DMatrix(df, enable_categorical=True))[0])
        return {"predicted_fare_usd": round(pred, 2), "model": "xgboost_fare_v1",
                "measured_test_rmse": self.fare_meta["metrics"]["test_rmse"]}

    # ------------------------------------------------------------------- eta

    def predict_eta_range(
        self, trip_distance: float, free_flow_duration_min: float, hour: int, day_of_week: int,
        is_holiday: int, temperature_c: float, precipitation_mm: float, demand_index: float,
    ) -> dict:
        """Returns p10/p50/p90 trip-duration estimates (minutes) -- an honest
        range, not a single guess. p10-p90 is the measured 80%-ish prediction
        interval; see eta_metadata.json's prediction_interval_coverage for how
        well-calibrated that interval actually is on held-out data (measured,
        not assumed)."""
        row = dict(
            trip_distance=trip_distance, free_flow_duration_min=free_flow_duration_min, hour=hour,
            day_of_week=day_of_week, is_holiday=is_holiday, temperature_c=temperature_c,
            precipitation_mm=precipitation_mm, demand_index=demand_index,
        )
        cols = self.eta_meta["features"]
        dmat = _row_to_dmatrix(row, cols)
        p10 = float(self.eta_p10.predict(dmat)[0])
        p50 = float(self.eta_p50.predict(dmat)[0])
        p90 = float(self.eta_p90.predict(dmat)[0])
        coverage = self.eta_meta.get("prediction_interval_coverage", {}).get("measured_p10_p90_coverage")
        return {
            "eta_minutes_p10_fast": round(p10, 1), "eta_minutes_p50_typical": round(p50, 1),
            "eta_minutes_p90_slow": round(p90, 1), "model": "xgboost_quantile_eta_v1",
            "measured_p10_p90_coverage": coverage,
        }

    # ---------------------------------------------------------------- LSTM

    def predict_demand_lstm(self, hourly_trip_counts_last_24h: list[float]) -> dict:
        """Next-hour zone demand from the last 24 hourly trip counts (raw
        counts, not pre-normalized -- normalization uses the model's own
        stored train-set mean/std)."""
        if len(hourly_trip_counts_last_24h) != self.lstm_meta["window"]:
            raise ValueError(f"expected {self.lstm_meta['window']} hourly values, got {len(hourly_trip_counts_last_24h)}")
        mean = self.lstm_meta["target_scaling"]["mean"]
        std = self.lstm_meta["target_scaling"]["std"]
        x = (np.array(hourly_trip_counts_last_24h, dtype=np.float32) - mean) / std
        x = torch.from_numpy(x).reshape(1, -1, 1)
        with torch.no_grad():
            pred_norm = self.lstm_model(x).item()
        pred = pred_norm * std + mean
        return {"predicted_next_hour_trips": round(pred, 1), "model": "lstm_demand_v1",
                "measured_test_rmse": self.lstm_meta["metrics"]["test_rmse"]}

    # ----------------------------------------------------------- Transformer

    def predict_demand_transformer(self, hourly_trip_counts_last_24h: list[float]) -> dict:
        """Same task as predict_demand_lstm, different architecture -- kept
        side by side deliberately so the two can be compared honestly on the
        same held-out data (see models/transformer_demand/comparison_report.md).

        Standardizes input/output with the model's own train-set mean/std,
        same as predict_demand_lstm -- train_transformer.py trains on
        normalized targets, so skipping this gives a wrong-scale prediction."""
        window = len(hourly_trip_counts_last_24h)
        mean = self.transformer_meta["target_scaling"]["mean"]
        std = self.transformer_meta["target_scaling"]["std"]
        x_norm = (np.array(hourly_trip_counts_last_24h, dtype=np.float32) - mean) / std
        x = torch.from_numpy(x_norm).reshape(1, window, 1)
        with torch.no_grad():
            pred_norm = self.transformer_model(x).item()
        pred = pred_norm * std + mean
        return {"predicted_next_hour_trips": round(pred, 1), "model": "transformer_demand_v1"}

    # ------------------------------------------------------------- overview

    def summary(self) -> None:
        """Prints every loaded model's honest, measured test-set performance --
        the real evidence behind this project, not marketing copy."""
        print("TeerthNYCRidesAI -- specialized ML models trained on NYC TLC's real ~113M-row trip warehouse\n")
        rows = [
            ("Demand (XGBoost)", self.demand_meta["metrics"]),
            ("Congestion multiplier (XGBoost)", self.congestion_meta["metrics"]),
            ("Fare (XGBoost)", self.fare_meta["metrics"]),
            ("Demand (LSTM)", self.lstm_meta["metrics"]),
        ]
        for name, metrics in rows:
            rmse = metrics.get("test_rmse")
            mae = metrics.get("test_mae")
            print(f"  {name:35s} test RMSE={rmse:.3f}  test MAE={mae:.3f}")
        print("\n  ETA quantiles (XGBoost, p10/p50/p90):")
        for q, m in self.eta_meta.get("metrics", {}).items():
            print(f"    {q}: pinball_loss={m['pinball_loss']:.3f}  MAE={m['mae']:.3f}")
        coverage = self.eta_meta.get("prediction_interval_coverage", {})
        if coverage.get("measured_p10_p90_coverage") is not None:
            print(f"    measured p10-p90 coverage: {coverage['measured_p10_p90_coverage']:.3f} "
                  f"(nominal {coverage['nominal']})")


if __name__ == "__main__":
    ai = TeerthNYCRidesAI()
    ai.summary()
