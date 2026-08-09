"""Phase 9: standardized city feature vector (E_city) for the global transfer
model (Phase 8).

Only uses columns verified to actually exist (IMPLEMENTATION_AUDIT.md
section 3): `global_cities` (population, lat/lon, model_status -- but
lat/lon are NULL for all 522 TRANSFER rows, verified by direct query, not
assumed), `cities` (mobility_mode, land_area_km2 -- only the 2 OBSERVED
rows), `worldmove_city_population` (population_density_mean -- the only
per-city density signal that exists for TRANSFER cities).

No infrastructure features (road density, transit density, etc.) are
included -- they do not exist anywhere in this repo's data, and inventing
placeholder values for them would violate rule 2 (no fabricated numbers).

Missing-data honesty: TRANSFER cities have no real latitude/longitude and
no confirmed mobility_mode in this repo. Rather than fabricate values,
each such gap gets an explicit `*_known` flag column, and the scaler's
training mean is reused as the fill value (`apply_scaler` does both jobs:
normalize + impute) -- so a TRANSFER city's missing lat/lon becomes
"average of the 2 training cities," a documented weak default, not an
invented real-looking coordinate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
SCALER_PATH = Path(__file__).resolve().parent / "city_feature_scaler.json"

# Raw (pre-scale) city feature columns -- see module docstring for provenance.
CITY_FEATURE_COLUMNS = [
    "population_log",
    "population_density",
    "latitude",
    "longitude",
    "is_cycle_share",
    "population_density_known",
    "latlon_known",
]


def build_city_feature_table(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """One row per city_id in `global_cities` (524 rows: 2 OBSERVED + 522
    TRANSFER), with raw (unscaled) feature columns populated from whatever
    real data exists for that city -- NaN where it genuinely doesn't."""
    global_cities = con.execute(
        "SELECT city_id, name, country_code, latitude, longitude, population, model_status FROM global_cities"
    ).df()
    cities = con.execute("SELECT id AS city_id, mobility_mode, land_area_km2 FROM cities").df()
    worldmove = con.execute(
        "SELECT country_code, city_name AS name, population_density_mean FROM worldmove_city_population"
    ).df()

    df = global_cities.merge(cities, on="city_id", how="left")
    df = df.merge(worldmove, on=["country_code", "name"], how="left")

    # population_density: land-area-derived for the 2 OBSERVED cities,
    # WorldMove-grid-derived for TRANSFER cities, NaN if neither exists.
    density_from_area = df["population"] / df["land_area_km2"]
    df["population_density"] = density_from_area.fillna(df["population_density_mean"])
    df["population_density_known"] = df["population_density"].notna().astype(int)

    df["latlon_known"] = df["latitude"].notna().astype(int)

    df["is_cycle_share"] = (df["mobility_mode"] == "cycle_share").astype(int)
    df["mobility_mode_unknown"] = df["mobility_mode"].isna().astype(int)

    df["population_log"] = np.log1p(df["population"])

    return df[
        ["city_id", "name", "country_code", "model_status", "mobility_mode_unknown", "population"]
        + CITY_FEATURE_COLUMNS
    ]


def fit_scaler(df: pd.DataFrame, columns: list[str] = CITY_FEATURE_COLUMNS) -> dict:
    """mean/std per column, NaN-ignoring. Fit ONLY on training rows (the 2
    OBSERVED cities' feature vectors) -- never on the 522 TRANSFER rows,
    which are inference-only covariates, never training labels or fit
    inputs (task requirement)."""
    return {
        col: {"mean": float(np.nanmean(df[col])), "std": float(np.nanstd(df[col]) or 1.0)}
        for col in columns
    }


def apply_scaler(df: pd.DataFrame, scaler: dict, columns: list[str] = CITY_FEATURE_COLUMNS) -> pd.DataFrame:
    """z-score each column, filling NaN with the scaler's own training mean
    first (so a missing value normalizes to exactly 0 -- "no information,"
    not a fabricated real-looking number)."""
    out = df.copy()
    for col in columns:
        mean, std = scaler[col]["mean"], scaler[col]["std"]
        out[col] = (out[col].fillna(mean) - mean) / std
    return out


def save_scaler(scaler: dict, path: Path = SCALER_PATH) -> None:
    path.write_text(json.dumps(scaler, indent=2))


def load_scaler(path: Path = SCALER_PATH) -> dict:
    return json.loads(path.read_text())


def demo() -> None:
    """Smallest runnable self-check: OBSERVED cities have every feature
    known; a synthetic TRANSFER-like row with NaNs scales to 0 for the
    missing columns after apply_scaler, not a fabricated value."""
    df = pd.DataFrame(
        {
            "population_log": [10.0, 12.0, np.nan],
            "population_density": [5000.0, 7000.0, np.nan],
            "latitude": [40.7, 51.5, np.nan],
            "longitude": [-74.0, -0.1, np.nan],
            "is_cycle_share": [0, 1, 0],
            "population_density_known": [1, 1, 0],
            "latlon_known": [1, 1, 0],
        }
    )
    train_rows = df.iloc[:2]  # the 2 "OBSERVED" cities
    scaler = fit_scaler(train_rows)
    scaled = apply_scaler(df, scaler)
    assert scaled.loc[2, "population_log"] == 0.0, "missing value should fill to the training mean -> z-score 0"
    assert scaled.loc[2, "latitude"] == 0.0
    assert not scaled.isna().any().any(), "no NaNs should survive apply_scaler"
    print("global_transfer build_features demo OK")


if __name__ == "__main__":
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    table = build_city_feature_table(con)
    n_transfer = (table["model_status"] == "TRANSFER").sum()
    n_observed = (table["model_status"] == "OBSERVED").sum()
    print(f"built city feature table: {len(table)} rows ({n_observed} OBSERVED, {n_transfer} TRANSFER)")
    print(f"lat/lon known for {table['latlon_known'].sum()} cities; population_density known for {table['population_density_known'].sum()}")
    train_scaler = fit_scaler(table[table["model_status"] == "OBSERVED"])
    save_scaler(train_scaler)
    print(f"saved scaler to {SCALER_PATH}")
    demo()
