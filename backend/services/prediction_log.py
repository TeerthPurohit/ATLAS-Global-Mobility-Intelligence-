"""SQLite-backed prediction log (ADR-007 follow-up). Same rationale as
rag/session_store.py: DuckDB's warehouse connection is read-only in
production (rule 8), and frequent small inserts don't belong on it anyway
-- stdlib sqlite3 avoids that contention entirely.

Not a retraining pipeline (that's Phase 3+, explicitly deferred) -- just an
honest, append-only record of what was asked and what was returned, so
future training data isn't lost by never having been captured.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "prediction_log.db"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target = Path(db_path) if db_path else DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(target))


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journey_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requested_at DATETIME NOT NULL,
                pickup_lat REAL NOT NULL,
                pickup_lon REAL NOT NULL,
                dropoff_lat REAL NOT NULL,
                dropoff_lon REAL NOT NULL,
                departure_time TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                fare_value TEXT,
                fare_basis TEXT,
                confidence_value REAL,
                response_json TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_predictions(limit: int = 50, db_path: Path | str | None = None) -> list[dict]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT id, requested_at, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
                   departure_time, vehicle_type, fare_value, fare_basis, confidence_value, response_json
            FROM journey_predictions ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def log_prediction(
    pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float,
    departure_time: str, vehicle_type: str, response: dict, db_path: Path | str | None = None,
) -> None:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        fare = response.get("fare", {})
        confidence = response.get("confidence", {})
        conn.execute(
            """
            INSERT INTO journey_predictions
                (requested_at, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
                 departure_time, vehicle_type, fare_value, fare_basis, confidence_value, response_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(), pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
                departure_time, vehicle_type, str(fare.get("value")), fare.get("basis"),
                confidence.get("value"), json.dumps(response, default=str),
            ),
        )
        conn.commit()
    finally:
        conn.close()
