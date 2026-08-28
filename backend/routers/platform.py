"""Platform-introspection endpoints (FR-10): health, warehouse stats/schema,
model registry metrics, algorithm benchmarks, dbt pipeline status, and mart
reads. Added to back widgets that were hardcoded in the frontend -- see
ARCHITECTURE_AUDIT.md for the widget-by-widget mapping.

Not part of the DomainError -> ErrorResponse migration (see backend/errors.py,
city.py/predictions.py/zones.py/chat.py/context.py): every route here just
returns whatever platform_service gives it, and that service layer already
degrades to an empty/partial result instead of raising -- there is no error
path in this router to migrate.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from loguru import logger

from backend.services import platform_service

router = APIRouter(tags=["platform"])


@router.get("/health")
def health() -> dict:
    logger.info("GET /health step=start")
    result = platform_service.check_health()
    logger.info("GET /health step=done status={}", result.get("status"))
    return result


@router.get("/dashboard/summary")
def dashboard_summary() -> dict:
    logger.info("GET /dashboard/summary step=start")
    result = platform_service.get_dashboard_summary()
    logger.info("GET /dashboard/summary step=done")
    return result


@router.get("/warehouse/stats")
def warehouse_stats() -> dict:
    logger.info("GET /warehouse/stats step=start")
    result = platform_service.get_warehouse_stats()
    logger.info("GET /warehouse/stats step=done")
    return result


@router.get("/warehouse/tables")
def warehouse_tables() -> list[dict]:
    logger.info("GET /warehouse/tables step=start")
    result = platform_service.get_warehouse_tables()
    logger.info("GET /warehouse/tables step=done count={}", len(result))
    return result


@router.get("/models/metrics")
def model_metrics() -> dict:
    logger.info("GET /models/metrics step=start")
    result = {
        "demand": platform_service.get_demand_model_metrics(),
        "fare": platform_service.get_fare_model_metrics(),
    }
    logger.info("GET /models/metrics step=done")
    return result


@router.get("/marts/zone_hourly_demand")
def mart_zone_hourly_demand() -> list[dict]:
    logger.info("GET /marts/zone_hourly_demand step=start")
    result = platform_service.get_hourly_demand_profile()
    logger.info("GET /marts/zone_hourly_demand step=done count={}", len(result))
    return result


@router.get("/marts/zone_demand_totals")
def mart_zone_demand_totals() -> list[dict]:
    logger.info("GET /marts/zone_demand_totals step=start")
    result = platform_service.get_zone_demand_totals()
    logger.info("GET /marts/zone_demand_totals step=done count={}", len(result))
    return result


@router.get("/algorithms/benchmarks")
def algorithm_benchmarks() -> dict:
    logger.info("GET /algorithms/benchmarks step=start")
    result = platform_service.get_algorithm_benchmarks()
    logger.info("GET /algorithms/benchmarks step=done")
    return result


@router.get("/pipeline/status")
def pipeline_status() -> dict:
    logger.info("GET /pipeline/status step=start")
    result = platform_service.get_pipeline_status()
    logger.info("GET /pipeline/status step=done")
    return result


@router.get("/capabilities/summary")
def capability_summary() -> dict:
    """Per-capability supported/unsupported counts across every registered
    city, counted from the registries themselves -- never a hardcoded total."""
    logger.info("GET /capabilities/summary step=start")
    result = platform_service.get_capability_summary()
    logger.info("GET /capabilities/summary step=done")
    return result


@router.get("/insights")
def insights(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    logger.info("GET /insights step=start limit={}", limit)
    result = platform_service.get_insight_docs(limit=limit)
    logger.info("GET /insights step=done count={}", len(result))
    return result
