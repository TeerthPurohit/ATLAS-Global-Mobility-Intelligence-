"""Cached per-city fare-structure profiles (ADR-011).

For NYC, a fare comes from a trained model (`model_service.predict_fare`).
For every other city there is no trip-level fare data anywhere in this
repo -- a `TariffProfile` is this project's honest substitute: a small,
cached set of linear-fare parameters (base fare, per-km, per-min, minimum
fare) in the city's *own currency*, generated once offline by an LLM call
anchored on NYC/London's real measured fares
(`scripts/generate_tariff_profile.py`), never on a request path (rule 8).

`pricing_engine.py` runs the arithmetic; the LLM never computes a price,
only supplies the parameters -- see ADR-011 for why this keeps rules.md
rule 1 ("SQL > algorithm > model > LLM call") intact: an LLM here is
supplying world knowledge (Mumbai's typical base fare) that no dataset in
this repo has, not aggregating, ranking, or guessing a number.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

TABLE_NAME = "city_tariff_profiles"
TABLE_COLUMNS = (
    "city_id", "currency", "base_fare", "per_km", "per_min", "min_fare",
    "night_multiplier", "airport_surcharge", "source", "generated_at",
    "model_id", "confidence", "notes",
)


@dataclass
class TariffProfile:
    city_id: str
    currency: str  # ISO 4217, e.g. "INR" -- every amount field below is IN THIS currency
    base_fare: float
    per_km: float
    per_min: float
    min_fare: float
    night_multiplier: float
    airport_surcharge: float
    source: Literal["measured", "llm_anchored"]
    generated_at: str
    model_id: str
    confidence: float
    notes: str


_profiles: dict[str, TariffProfile] = {}


def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    """Called only from the offline generation/calibration scripts (they
    hold the sole write connection) -- the running backend only ever reads
    (see load() below), so it never needs to create this table itself."""
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            city_id VARCHAR PRIMARY KEY,
            currency VARCHAR,
            base_fare DOUBLE,
            per_km DOUBLE,
            per_min DOUBLE,
            min_fare DOUBLE,
            night_multiplier DOUBLE,
            airport_surcharge DOUBLE,
            source VARCHAR,
            generated_at TIMESTAMP,
            model_id VARCHAR,
            confidence DOUBLE,
            notes VARCHAR
        )
        """
    )


def load() -> None:
    """Read-only at startup (rule 8: no write lock ever taken by the live
    server). A missing table just means no profile has been generated yet
    -- every city falls back to `unavailable`, never a crash."""
    _profiles.clear()
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        exists = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [TABLE_NAME]
        ).fetchone()[0] > 0
        if not exists:
            return
        rows = con.execute(f"SELECT {', '.join(TABLE_COLUMNS)} FROM {TABLE_NAME}").fetchall()
    finally:
        con.close()
    for row in rows:
        data = dict(zip(TABLE_COLUMNS, row))
        data["generated_at"] = str(data["generated_at"])
        _profiles[data["city_id"]] = TariffProfile(**data)


def get(city_id: str) -> TariffProfile | None:
    if not _profiles:
        load()  # defensive lazy-load -- see backend/registry/cities.py's get_city() for why
    return _profiles.get(city_id)


def upsert(profile: TariffProfile) -> None:
    """Offline-only write path (scripts/generate_tariff_profile.py,
    scripts/calibrate_tariff_nyc.py). Never called from a FastAPI route."""
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=False)
    try:
        ensure_table(con)
        con.execute(f"DELETE FROM {TABLE_NAME} WHERE city_id = ?", [profile.city_id])
        placeholders = ", ".join(["?"] * len(TABLE_COLUMNS))
        con.execute(
            f"INSERT INTO {TABLE_NAME} ({', '.join(TABLE_COLUMNS)}) VALUES ({placeholders})",
            [getattr(profile, col) for col in TABLE_COLUMNS],
        )
    finally:
        con.close()
