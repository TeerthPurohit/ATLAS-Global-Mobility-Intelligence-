"""Platform-introspection endpoints (FR-10): health, warehouse stats/schema,
model registry metrics, algorithm benchmarks, dbt pipeline status, and mart
reads. Added to back widgets that were hardcoded in the frontend -- see
ARCHITECTURE_AUDIT.md for the widget-by-widget mapping.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.services import platform_service

router = APIRouter(tags=["platform"])


@router.get("/health")
def health() -> dict:
    return platform_service.check_health()


@router.get("/dashboard/summary")
def dashboard_summary() -> dict:
    return platform_service.get_dashboard_summary()


@router.get("/warehouse/stats")
def warehouse_stats() -> dict:
    return platform_service.get_warehouse_stats()


@router.get("/warehouse/tables")
def warehouse_tables() -> list[dict]:
    return platform_service.get_warehouse_tables()


@router.get("/models/metrics")
def model_metrics() -> dict:
    return {
        "demand": platform_service.get_demand_model_metrics(),
        "fare": platform_service.get_fare_model_metrics(),
    }


@router.get("/marts/zone_hourly_demand")
def mart_zone_hourly_demand() -> list[dict]:
    return platform_service.get_hourly_demand_profile()


@router.get("/algorithms/benchmarks")
def algorithm_benchmarks() -> dict:
    return platform_service.get_algorithm_benchmarks()


@router.get("/pipeline/status")
def pipeline_status() -> dict:
    return platform_service.get_pipeline_status()


@router.get("/capabilities/summary")
def capability_summary() -> dict:
    """Per-capability supported/unsupported counts across every registered
    city, counted from the registries themselves -- never a hardcoded total."""
    return platform_service.get_capability_summary()


@router.get("/insights")
def insights(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    return platform_service.get_insight_docs(limit=limit)
