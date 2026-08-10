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

import logging
import re
import sys
from dataclasses import dataclass, fields
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

logger = logging.getLogger(__name__)

TABLE_NAME = "city_tariff_profiles"
# The original 13 columns every existing row has. Optional columns added later
# (below) are read only when the table actually has them, so a warehouse built
# before this change still loads -- see load().
TABLE_COLUMNS = (
    "city_id", "currency", "base_fare", "per_km", "per_min", "min_fare",
    "night_multiplier", "airport_surcharge", "source", "generated_at",
    "model_id", "confidence", "notes",
)
# name -> DuckDB type, all nullable: a component is applied to a fare ONLY if
# this city's profile actually defines it (pricing_engine._base_fare_tariff).
OPTIONAL_COLUMNS: dict[str, str] = {
    "booking_fee": "DOUBLE",
    "platform_fee": "DOUBLE",
    "tolls": "DOUBLE",
    "peak_multiplier": "DOUBLE",
    "vehicle_multiplier": "DOUBLE",
    "surge_multiplier": "DOUBLE",
    "effective_from": "VARCHAR",
    "version": "VARCHAR",
    "source_type": "VARCHAR",
}

# `source` stays as-is (existing rows are all "llm_anchored"); `source_type` is
# the finer-grained provenance the newer profiles carry. "derived"/"llm_anchored"
# map onto the old two values, the other three are for real published tariffs.
SourceType = Literal["official", "operator", "regulatory", "derived", "llm_anchored"]
_SOURCE_TYPES = ("official", "operator", "regulatory", "derived", "llm_anchored")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_NON_NEGATIVE = (
    "base_fare", "per_km", "per_min", "min_fare", "airport_surcharge",
    "booking_fee", "platform_fee", "tolls",
)
_MULTIPLIERS = ("night_multiplier", "peak_multiplier", "vehicle_multiplier", "surge_multiplier")


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
    # Optional components -- None means "this city's tariff does not define
    # it", and pricing_engine must then not apply it at all (never a default
    # that silently invents a fee the city doesn't charge).
    booking_fee: float | None = None
    platform_fee: float | None = None
    tolls: float | None = None
    peak_multiplier: float | None = None
    vehicle_multiplier: float | None = None
    surge_multiplier: float | None = None
    effective_from: str | None = None  # ISO date
    version: str | None = None
    source_type: SourceType | None = None

    def __post_init__(self) -> None:
        """Validation at construction, so it holds on BOTH paths -- the
        offline upsert and the startup load -- and a malformed profile can
        never reach a live fare calculation."""
        if not _CURRENCY_RE.match(self.currency or ""):
            raise ValueError(f"invalid ISO 4217 currency {self.currency!r} for city_id={self.city_id!r}")
        for name in _NON_NEGATIVE:
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be >= 0, got {value!r} for city_id={self.city_id!r}")
        for name in _MULTIPLIERS:
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be > 0, got {value!r} for city_id={self.city_id!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence!r} for city_id={self.city_id!r}")
        if self.source_type is not None and self.source_type not in _SOURCE_TYPES:
            raise ValueError(f"invalid source_type {self.source_type!r} for city_id={self.city_id!r}")
        if self.effective_from:
            try:
                datetime.fromisoformat(str(self.effective_from))
            except ValueError as exc:
                raise ValueError(
                    f"malformed effective_from {self.effective_from!r} for city_id={self.city_id!r}"
                ) from exc


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
    # Additive migration: older warehouses have the 13-column table only.
    existing = {r[0] for r in con.execute(f"DESCRIBE {TABLE_NAME}").fetchall()}
    for name, sql_type in OPTIONAL_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {name} {sql_type}")


def _present_columns(con: duckdb.DuckDBPyConnection) -> tuple[str, ...]:
    existing = {r[0] for r in con.execute(f"DESCRIBE {TABLE_NAME}").fetchall()}
    return tuple(f.name for f in fields(TariffProfile) if f.name in existing)


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
        columns = _present_columns(con)
        rows = con.execute(f"SELECT {', '.join(columns)} FROM {TABLE_NAME}").fetchall()
    finally:
        con.close()
    for row in rows:
        data = {k: v for k, v in zip(columns, row) if v is not None}
        data["generated_at"] = str(data.get("generated_at"))
        if isinstance(data.get("effective_from"), (date, datetime)):
            data["effective_from"] = data["effective_from"].isoformat()
        try:
            _profiles[data["city_id"]] = TariffProfile(**data)
        except (TypeError, ValueError) as exc:
            # A malformed row is dropped, never served: the city degrades to
            # an honest `unavailable` fare instead of a validated-away price.
            logger.warning("skipping invalid tariff profile row %s: %s", data.get("city_id"), exc)


def get(city_id: str) -> TariffProfile | None:
    if not _profiles:
        load()  # defensive lazy-load -- see backend/registry/cities.py's get_city() for why
    return _profiles.get(city_id)


def city_ids() -> list[str]:
    """Every city_id that actually has a cached profile -- the real
    fare-supported set, read from the loaded table, never assumed from a tier."""
    if not _profiles:
        load()
    return list(_profiles)


def upsert(profile: TariffProfile) -> None:
    """Offline-only write path (scripts/generate_tariff_profile.py,
    scripts/calibrate_tariff_nyc.py). Never called from a FastAPI route."""
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=False)
    try:
        ensure_table(con)  # also adds any missing optional columns
        columns = _present_columns(con)
        con.execute(f"DELETE FROM {TABLE_NAME} WHERE city_id = ?", [profile.city_id])
        placeholders = ", ".join(["?"] * len(columns))
        con.execute(
            f"INSERT INTO {TABLE_NAME} ({', '.join(columns)}) VALUES ({placeholders})",
            [getattr(profile, col) for col in columns],
        )
    finally:
        con.close()
