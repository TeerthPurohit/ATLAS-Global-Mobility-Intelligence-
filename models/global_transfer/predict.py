"""Phase 8: inference for the joint global transfer model.

For the 2 OBSERVED cities, pass real recent-history `lag_overrides` (from
`zone_hourly_demand`/`london_station_hourly_demand`) and this is a genuine
forecast, `basis="computed"`.

For the 522 TRANSFER-tier cities there is no trip-level history at all --
no real lag_1h/lag_24h/lag_168h/ewma/rolling_7d_avg exists. Rather than
crash or invent a lag value, `_fallback_temporal_proxy()` substitutes a
population-per-capita hourly rate (reusing the already-honest, already
N=2-caveated `models/cross_city_estimation/estimate.py`) for every lag/EWMA/
rolling feature. This is a materially weaker "prediction" than a real
forecast -- it is population-scaling wearing an XGBoost costume for one
call -- so it is always tagged `basis="modeled_estimate"` and the `reason`
string says so plainly, mirroring the rest of this repo's basis discipline
(never `"computed"` for a TRANSFER-tier estimate).

Missing WorldMove/city-feature data for a requested city_id is handled by
returning `basis="unavailable"` with a reason, never by raising or crashing
(task requirement, tested in
`tests/test_global_transfer_missing_worldmove.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import xgboost as xgb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from models.cross_city_estimation.estimate import estimate_demand_per_capita  # noqa: E402
from models.global_transfer.build_features import (  # noqa: E402
    CITY_FEATURE_COLUMNS,
    apply_scaler,
    build_city_feature_table,
    load_scaler,
)
from models.global_transfer.train_global import FEATURE_COLUMNS, TEMPORAL_FEATURE_COLUMNS  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent
NYC_DB = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

_LAG_KEYS = ["lag_1h", "lag_24h", "lag_168h", "ewma", "rolling_7d_avg"]


def load_model(artifact_dir: Path = ARTIFACT_DIR) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor()
    model.load_model(str(artifact_dir / "xgb_model.json"))
    return model


def _fallback_temporal_proxy(population: float) -> dict:
    """No real trip history exists for a TRANSFER city -- substitute a flat
    population-per-capita hourly rate for every lag/EWMA/rolling feature.
    Documented weak fallback, not a forecast."""
    daily_estimate, _ = estimate_demand_per_capita(int(population))
    hourly_rate = daily_estimate / 24.0
    return {k: hourly_rate for k in _LAG_KEYS}


def predict(
    city_id: str,
    hour: int,
    day_of_week: int,
    temperature_c: float = 0.0,
    precipitation_mm: float = 0.0,
    lag_overrides: dict | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
    model: xgb.XGBRegressor | None = None,
) -> dict:
    """Returns {"value": float | None, "basis": str, "reason": str}."""
    owns_con = con is None
    con = con or duckdb.connect(str(NYC_DB), read_only=True)
    try:
        city_table = build_city_feature_table(con)
    except duckdb.Error as exc:  # e.g. worldmove_city_population table missing
        return {"value": None, "basis": "unavailable", "reason": f"city feature lookup failed: {exc}"}
    finally:
        if owns_con:
            con.close()

    row = city_table[city_table["city_id"] == city_id]
    if row.empty:
        return {"value": None, "basis": "unavailable", "reason": f"unknown city_id={city_id!r} (not in global_cities)"}
    row = row.iloc[0]

    scaler = load_scaler()
    scaled_row = apply_scaler(row.to_frame().T, scaler).iloc[0]
    city_feats = {col: float(scaled_row[col]) for col in CITY_FEATURE_COLUMNS}

    is_observed = row["model_status"] == "OBSERVED"
    if lag_overrides is not None:
        temporal_extra = lag_overrides
        basis = "computed" if is_observed else "modeled_estimate"
        reason = "real recent-history lag features supplied by caller"
    else:
        temporal_extra = _fallback_temporal_proxy(float(row["population"]))
        basis = "modeled_estimate"
        reason = (
            "no real trip-level history for this city -- lag/EWMA/rolling features "
            "substituted with a population-per-capita hourly-rate proxy "
            "(models/cross_city_estimation/estimate.py); treat as order-of-magnitude "
            "only, not a real forecast"
        )

    features = {
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week in (5, 6)),
        "temperature_c": temperature_c,
        "precipitation_mm": precipitation_mm,
        **temporal_extra,
        **city_feats,
    }
    x = pd.DataFrame([features])[FEATURE_COLUMNS]

    model = model or load_model()
    value = float(model.predict(x)[0])
    return {"value": value, "basis": basis, "reason": reason}


def demo() -> None:
    """Smallest runnable self-check: a known OBSERVED city predicts without
    crashing, and an unknown city_id degrades gracefully instead of raising."""
    con = duckdb.connect(str(NYC_DB), read_only=True)
    model = load_model()
    try:
        result = predict("nyc", hour=8, day_of_week=1, con=con, model=model)
        assert result["value"] is not None and result["basis"] in ("computed", "modeled_estimate")

        result_transfer = predict("FR_DIJON", hour=8, day_of_week=1, con=con, model=model)
        assert result_transfer["value"] is not None
        assert result_transfer["basis"] == "modeled_estimate"

        result_unknown = predict("NOT_A_REAL_CITY", hour=8, day_of_week=1, con=con, model=model)
        assert result_unknown["value"] is None and result_unknown["basis"] == "unavailable"
    finally:
        con.close()
    print("global_transfer predict demo OK")


if __name__ == "__main__":
    demo()
