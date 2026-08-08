"""Model registry (SPEC-013 FR-4) -- thin query module over the seeded
`model_registry` dbt table, loaded once at startup (rule 8: a handful of
rows, not a table-scan concern).

Catalogs artifacts that already exist on disk; never retrains anything.
`load()` validates every `artifact_path` exists relative to the repo root --
a row that claims `status="active"` but whose file is missing is demoted to
`"unavailable"` here rather than crashing startup or silently serving a
prediction with no backing artifact (rule 2).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

logger = logging.getLogger(__name__)

# model_id -> row. model_id is the same string model_service.py already
# returns as its `model_name` (e.g. "xgboost_demand_v1"), so callers can look
# a prediction's actual model up directly, not just the "primary" one.
_models: dict[str, dict] = {}


def load() -> None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        rows = con.execute(
            "select model_id, city_id, metric, model_type, version, artifact_path, "
            "training_period, status, metrics_ref from model_registry"
        ).fetchall()
    finally:
        con.close()

    _models.clear()
    for model_id, city_id, metric, model_type, version, artifact_path, training_period, status, metrics_ref in rows:
        resolved_status = status
        if status == "active" and not (REPO_ROOT / artifact_path).exists():
            resolved_status = "unavailable"
            logger.warning(
                "model_registry row %s (%s/%s) references missing artifact %s; demoting to unavailable",
                model_id, city_id, metric, artifact_path,
            )
        _models[model_id] = {
            "model_id": model_id,
            "city_id": city_id,
            "metric": metric,
            "model_type": model_type,
            "version": version,
            "artifact_path": artifact_path,
            "training_period": training_period,
            "status": resolved_status,
            "metrics_ref": metrics_ref,
        }


def get_model(model_id: str) -> dict | None:
    return _models.get(model_id)


def list_models_for(city_id: str, metric: str | None = None) -> list[dict]:
    return [
        m for m in _models.values()
        if m["city_id"] == city_id and (metric is None or m["metric"] == metric)
    ]


def resolve_model(city_id: str, metric: str) -> dict | None:
    """The active model backing `metric` for `city_id`, or None if the
    capability isn't really wired (used as the capability gate)."""
    for m in list_models_for(city_id, metric):
        if m["status"] == "active":
            logger.info("model resolution city_id=%s metric=%s -> %s", city_id, metric, m["model_id"])
            return m
    logger.info("model resolution city_id=%s metric=%s -> none", city_id, metric)
    return None


def has_active_model(city_id: str) -> bool:
    return any(m["status"] == "active" for m in _models.values() if m["city_id"] == city_id)
