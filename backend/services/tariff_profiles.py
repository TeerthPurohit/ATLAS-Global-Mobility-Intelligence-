"""Cached per-city fare-structure profiles.

A `TariffProfile` is a small set of linear-fare parameters (base fare,
per-km, per-min, minimum fare) in a city's own currency, used where that
city has no trained fare model. `pricing_engine.py` runs the arithmetic.

Since ADR-011 only NYC and London are served, and both have real measured
fares behind them: NYC prices from a trained model
(`model_service.predict_fare`), and both cities' cached profiles are
calibrated against real fare data (`scripts/calibrate_tariff_nyc.py`),
not generated. The offline LLM-anchored generation path that produced the
other ~515 profiles was removed with the global layer -- see ADR-011 for
why those profiles were not trustworthy enough to keep.

Storage (2026-08-16 migration): this table lives in the same RDS Postgres
instance as `prediction_log.py` / `rag/session_store.py` (ADR-009), reached
through the same shared SQLAlchemy engine -- not DuckDB. Postgres is the
SOLE SOURCE OF TRUTH for `city_tariff_profiles`; every other table in this
repo's DuckDB warehouse is still authoritative as before.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, fields
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from loguru import logger
from sqlalchemy import Column, DateTime, Double, String, Table, Text, select
from sqlalchemy.exc import SQLAlchemyError

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from db import Base, get_connection, get_engine  # noqa: E402

# Historical-only: DuckDB's copy of this table (see module docstring -- it's a
# frozen, no-longer-written stale mirror). Kept solely so
# scripts/backfill_tariff_extras.py (a completed, one-time 2026-08-13/14 run)
# still imports cleanly if anyone re-runs it; nothing in this module reads or
# writes through this path anymore.
WAREHOUSE_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"

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
    # Completion marker for scripts/backfill_tariff_extras.py -- NOT the same
    # question as "is peak_multiplier set". A city can honestly have no
    # peak/surge pricing at all (a real LLM answer, not a missing one), so
    # peak_multiplier IS NULL is indistinguishable from "never backfilled"
    # and caused exactly that bug (found running the backfill 2026-08-14:
    # 250 already-processed cities kept re-queuing every run). This column
    # only ever means "the backfill pass has run for this row".
    "extras_backfilled_at": "TIMESTAMP",
    # Evidence-grounded regeneration (found 2026-08-16: 72% of the original
    # 517 llm_anchored profiles were near-duplicates of another city's numbers
    # -- a cheap model at low temperature with no external grounding converges
    # on generic per-currency templates instead of reasoning per-city). These
    # three columns record what scripts/generate_tariff_profile.py's
    # propose-then-validate path actually had to go on, so `confidence` stops
    # being an LLM's unverifiable self-rating and starts being derived from
    # real corroboration -- see _confidence_from_validation().
    "evidence_sources": "VARCHAR",  # JSON list of {source, url} actually used, [] if none found
    "validation_method": "VARCHAR",  # web_search_corroborated | web_search_partial | llm_only_fallback
    "validated_at": "TIMESTAMP",
}
VALIDATION_METHODS = (
    "web_search_corroborated", "web_search_partial", "analytical_only", "llm_only_fallback",
)

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
    extras_backfilled_at: str | None = None  # ISO timestamp -- see OPTIONAL_COLUMNS comment
    evidence_sources: str | None = None  # JSON list of {source, url}, see OPTIONAL_COLUMNS comment
    validation_method: str | None = None
    validated_at: str | None = None  # ISO timestamp

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
        if self.validation_method is not None and self.validation_method not in VALIDATION_METHODS:
            raise ValueError(f"invalid validation_method {self.validation_method!r} for city_id={self.city_id!r}")
        if self.effective_from:
            try:
                datetime.fromisoformat(str(self.effective_from))
            except ValueError as exc:
                raise ValueError(
                    f"malformed effective_from {self.effective_from!r} for city_id={self.city_id!r}"
                ) from exc


_profiles: dict[str, TariffProfile] = {}

# Timestamp-typed columns are converted to/from ISO strings at the
# load()/upsert() boundary, so TariffProfile's own field types (all `str |
# None`, never a datetime) don't change for any caller -- same contract the
# old DuckDB path had.
_TIMESTAMP_FIELDS = ("generated_at", "extras_backfilled_at", "validated_at")


class CityTariffProfile(Base):
    __tablename__ = TABLE_NAME

    city_id = Column(String, primary_key=True)
    currency = Column(String)
    base_fare = Column(Double)
    per_km = Column(Double)
    per_min = Column(Double)
    min_fare = Column(Double)
    night_multiplier = Column(Double)
    airport_surcharge = Column(Double)
    source = Column(String)
    generated_at = Column(DateTime(timezone=True))
    model_id = Column(String)
    confidence = Column(Double)
    notes = Column(Text)
    booking_fee = Column(Double)
    platform_fee = Column(Double)
    tolls = Column(Double)
    peak_multiplier = Column(Double)
    vehicle_multiplier = Column(Double)
    surge_multiplier = Column(Double)
    effective_from = Column(String)
    version = Column(String)
    source_type = Column(String)
    extras_backfilled_at = Column(DateTime(timezone=True))
    evidence_sources = Column(Text)
    validation_method = Column(String)
    validated_at = Column(DateTime(timezone=True))


def _table_for(table_name: str) -> Table:
    # table_name is only ever overridden by tests -- production always uses
    # TABLE_NAME. Same helper as prediction_log.py/session_store.py.
    if table_name in Base.metadata.tables:
        return Base.metadata.tables[table_name]
    return CityTariffProfile.__table__.to_metadata(Base.metadata, name=table_name)


def ensure_table(conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    """Idempotent create -- called from load() and upsert() the same way
    prediction_log.py's init_db() is, so neither path needs the table to
    already exist."""
    _table_for(table_name).create(get_engine(conninfo), checkfirst=True)


def load(conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    """Startup read (rule 8: no work on the request path -- this is called
    once at app startup and thereafter only defensively/lazily, never per
    request). Postgres unreachable degrades to an empty cache -- every city
    then honestly serves `unavailable` instead of crashing the backend, same
    contract session_store.py/prediction_log.py use for this RDS instance
    (ADR-009: unreachable outside the VPC is expected, not exceptional)."""
    logger.info("tariff_profiles.load step=start table={}", table_name)
    _profiles.clear()
    try:
        ensure_table(conninfo, table_name)
        table = _table_for(table_name)
        with get_connection(conninfo) as conn:
            rows = conn.execute(select(table)).mappings().all()
    except SQLAlchemyError as exc:
        logger.warning("tariff_profiles.load step=query failed (every city serves unavailable fare): {}", exc)
        return
    for row in rows:
        data = {k: v for k, v in dict(row).items() if v is not None}
        for name in _TIMESTAMP_FIELDS:
            if isinstance(data.get(name), (date, datetime)):
                data[name] = data[name].isoformat()
        try:
            _profiles[data["city_id"]] = TariffProfile(**data)
        except (TypeError, ValueError) as exc:
            # A malformed row is dropped, never served: the city degrades to
            # an honest `unavailable` fare instead of a validated-away price.
            logger.warning("tariff_profiles.load step=row_validation failed city_id={} reason={}", data.get("city_id"), exc)
    logger.info("tariff_profiles.load step=done count={}", len(_profiles))


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


def upsert(profile: TariffProfile, conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    """Offline-only write path (scripts/generate_tariff_profile.py,
    scripts/validate_tariff_city.py, scripts/calibrate_tariff_nyc.py). Never
    called from a FastAPI route -- and, per ADR-009/rule 8, never called from
    the live backend process at all now: this is Postgres, reached from
    whatever machine runs the offline script (including a Claude Code cloud
    routine's isolated sandbox, which is the whole reason this table moved
    off the local DuckDB file -- see module docstring)."""
    ensure_table(conninfo, table_name)
    table = _table_for(table_name)
    values = {f.name: getattr(profile, f.name) for f in fields(TariffProfile)}
    for name in _TIMESTAMP_FIELDS:  # DateTime columns need a datetime, not the dataclass's ISO str
        if values[name] is not None:
            values[name] = datetime.fromisoformat(values[name])
    with get_engine(conninfo).begin() as conn:
        conn.execute(table.delete().where(table.c.city_id == profile.city_id))
        conn.execute(table.insert().values(**values))
