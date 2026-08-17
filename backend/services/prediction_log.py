"""Postgres-backed prediction log (ADR-007 follow-up, migrated off SQLite
per ADR-009's RDS operational store). Same rationale as
rag/session_store.py: DuckDB's warehouse connection is read-only in
production (rule 8), and frequent small inserts don't belong on it anyway
-- a real Postgres connection avoids that contention and gives concurrent
writers (multiple backend instances) a shared, durable log instead of a
per-instance SQLite file.

Not a retraining pipeline (that's Phase 3+, explicitly deferred) -- just an
honest, append-only record of what was asked and what was returned, so
future training data isn't lost by never having been captured.

Every public function below degrades to a no-op/empty result on a
`psycopg.Error` instead of raising -- same reasoning and same root cause as
rag/session_store.py's identical guard: the RDS instance is deliberately
private (ADR-009), so a deployment outside its VPC seeing it as unreachable
is expected, not exceptional. Before this guard, `POST /journey/estimate`
computed a fully valid result and then discarded it, returning a 500,
because this optional analytics write was unconditional (found via /debug
2026-08-13 -- the same pattern also broke GET /journey/history and
/api/analytics/{summary,history,trends}).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

TABLE_NAME = "journey_predictions"


def get_connection(conninfo: str | None = None) -> psycopg.Connection:
    dsn = conninfo or os.environ["DATABASE_URL"]
    sslrootcert = os.environ.get("POSTGRES_SSLROOTCERT", "certs/global-bundle.pem")
    # See rag/session_store.py's identical get_connection() for why this needs
    # an explicit timeout -- without it, a private-VPC RDS instance that's
    # simply unreachable blocks on the OS-level TCP timeout (60s+).
    return psycopg.connect(
        dsn, sslmode="verify-full", sslrootcert=sslrootcert, row_factory=dict_row, connect_timeout=3
    )


def init_db(conninfo: str | None = None, table_name: str = TABLE_NAME) -> None:
    with get_connection(conninfo) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                requested_at TIMESTAMPTZ NOT NULL,
                pickup_lat DOUBLE PRECISION NOT NULL,
                pickup_lon DOUBLE PRECISION NOT NULL,
                dropoff_lat DOUBLE PRECISION NOT NULL,
                dropoff_lon DOUBLE PRECISION NOT NULL,
                departure_time TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                fare_value TEXT,
                fare_basis TEXT,
                confidence_value DOUBLE PRECISION,
                city_id TEXT,
                response_json TEXT NOT NULL
            )
            """
        )
        # Additive migration: rows/tables created before city_id existed keep working.
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS city_id TEXT")
        conn.commit()


def get_recent_predictions(limit: int = 50, conninfo: str | None = None, table_name: str = TABLE_NAME) -> list[dict]:
    try:
        init_db(conninfo, table_name)
        with get_connection(conninfo) as conn:
            cur = conn.execute(
                f"""
                SELECT id, requested_at, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
                       departure_time, vehicle_type, fare_value, fare_basis, confidence_value, city_id, response_json
                FROM {table_name} ORDER BY id DESC LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            for row in rows:
                row["requested_at"] = row["requested_at"].isoformat()
            return rows
    except psycopg.Error as exc:
        logger.warning("prediction_log.get_recent_predictions degraded (returning empty): %s", exc)
        return []


def log_prediction(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    departure_time: str, vehicle_type: str, response: dict,
    conninfo: str | None = None, table_name: str = TABLE_NAME,
) -> None:
    try:
        init_db(conninfo, table_name)
        with get_connection(conninfo) as conn:
            fare = response.get("fare", {})
            confidence = response.get("confidence", {})
            conn.execute(
                f"""
                INSERT INTO {table_name}
                    (requested_at, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
                     departure_time, vehicle_type, fare_value, fare_basis, confidence_value, city_id, response_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    datetime.now(timezone.utc), pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
                    departure_time, vehicle_type, str(fare.get("value")), fare.get("basis"),
                    confidence.get("value"), response.get("city_id"), json.dumps(response, default=str),
                ),
            )
            conn.commit()
    except psycopg.Error as exc:
        logger.warning("prediction_log.log_prediction degraded (journey estimate not logged): %s", exc)
