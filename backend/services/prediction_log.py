"""Postgres-backed prediction log (ADR-007 follow-up, migrated off SQLite
per ADR-009's RDS operational store, and off raw psycopg onto SQLAlchemy).
Same rationale as rag/session_store.py: DuckDB's warehouse connection is
read-only in production (rule 8), and frequent small inserts don't belong
on it anyway -- a real Postgres connection avoids that contention and gives
concurrent writers (multiple backend instances) a shared, durable log
instead of a per-instance SQLite file.

Not a retraining pipeline (that's Phase 3+, explicitly deferred) -- just an
honest, append-only record of what was asked and what was returned, so
future training data isn't lost by never having been captured.

Every public function below degrades to a no-op/empty result on a
`SQLAlchemyError` instead of raising -- same guard as rag/session_store.py's
identical one. Originally guarded against RDS being deliberately private
(ADR-009); migrated to Neon 2026-08-28 (publicly reachable), but the
degrade-gracefully contract stays. Before this guard, `POST /journey/estimate`
computed a fully valid result and then discarded it, returning a 500,
because this optional analytics write was unconditional (found via /debug
2026-08-13 -- the same pattern also broke GET /journey/history and
/api/analytics/{summary,history,trends}).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy import Column, DateTime, Double, Integer, String, Table, Text, select
from sqlalchemy.exc import SQLAlchemyError

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from db import Base, get_connection, get_engine  # noqa: E402

TABLE_NAME = "journey_predictions"


class JourneyPrediction(Base):
    __tablename__ = TABLE_NAME

    id = Column(Integer, primary_key=True)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    pickup_lat = Column(Double, nullable=False)
    pickup_lon = Column(Double, nullable=False)
    dropoff_lat = Column(Double, nullable=False)
    dropoff_lon = Column(Double, nullable=False)
    departure_time = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    fare_value = Column(String)
    fare_basis = Column(String)
    confidence_value = Column(Double)
    city_id = Column(String)
    response_json = Column(Text, nullable=False)


def _table_for(table_name: str) -> Table:
    # table_name is only ever overridden by tests -- production always uses
    # the default TABLE_NAME. See rag/session_store.py's identical helper.
    if table_name in Base.metadata.tables:
        return Base.metadata.tables[table_name]
    return JourneyPrediction.__table__.to_metadata(Base.metadata, name=table_name)


def init_db(conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    engine = get_engine(conninfo)
    table = _table_for(table_name)
    table.create(engine, checkfirst=True)
    # Additive migration: tables created before city_id existed keep working.
    with engine.begin() as conn:
        conn.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS city_id TEXT')


def get_recent_predictions(limit: int = 50, conninfo: str | None = None, table_name: str = TABLE_NAME) -> list[dict]:
    logger.debug("prediction_log.get_recent_predictions step=start limit={}", limit)
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        with get_connection(conninfo) as conn:
            rows = conn.execute(select(table).order_by(table.c.id.desc()).limit(limit)).mappings()
            result = []
            for row in rows:
                row = dict(row)
                row["requested_at"] = row["requested_at"].isoformat()
                result.append(row)
            logger.debug("prediction_log.get_recent_predictions step=done count={}", len(result))
            return result
    except SQLAlchemyError as exc:
        logger.warning("prediction_log.get_recent_predictions step=query failed (returning empty): {}", exc)
        return []


def log_prediction(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    departure_time: str, vehicle_type: str, response: dict,
    conninfo: str | None = None, table_name: str = TABLE_NAME,
) -> None:
    logger.debug("prediction_log.log_prediction step=start city_id={}", response.get("city_id"))
    try:
        init_db(conninfo, table_name)
        table = _table_for(table_name)
        fare = response.get("fare", {})
        confidence = response.get("confidence", {})
        with get_engine(conninfo).begin() as conn:
            conn.execute(table.insert().values(
                requested_at=datetime.now(timezone.utc),
                pickup_lat=pickup_lat, pickup_lon=pickup_lon,
                dropoff_lat=dropoff_lat, dropoff_lon=dropoff_lon,
                departure_time=departure_time, vehicle_type=vehicle_type,
                fare_value=str(fare.get("value")), fare_basis=fare.get("basis"),
                confidence_value=confidence.get("value"), city_id=response.get("city_id"),
                response_json=json.dumps(response, default=str),
            ))
        logger.debug("prediction_log.log_prediction step=done")
    except SQLAlchemyError as exc:
        logger.warning("prediction_log.log_prediction step=insert failed (journey estimate not logged): {}", exc)
