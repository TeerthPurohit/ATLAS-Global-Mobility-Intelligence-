"""Analytics APIs (Part 13 of API Decomposition).

Frontend dashboard analytics operating on prediction logs/warehouse data.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Query

# Add repo root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb

from backend.schemas import (  # noqa: E402
    AnalyticsHistoryResponse,
    AnalyticsInsightsResponse,
    AnalyticsSummaryResponse,
    AnalyticsTrendsResponse,
)
from backend.services import platform_service, prediction_log  # noqa: E402

WAREHOUSE_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "nyc_rides.duckdb"

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def summary() -> AnalyticsSummaryResponse:
    """Analytics summary from prediction logs and warehouse."""
    # Get prediction log stats
    history = prediction_log.get_recent_predictions(limit=10000)
    total_predictions = len(history)

    # Get unique cities served
    cities_served = set()
    for h in history:
        # Logs may not have city_id, fall back to 1 for NYC
        cities_served.add("nyc")

    # Date range from logs
    if history:
        dates = [h.get("timestamp") for h in history if h.get("timestamp")]
        if dates:
            date_range = {
                "start": min(dates),
                "end": max(dates),
            }
        else:
            date_range = {"start": None, "end": None}
    else:
        date_range = {"start": None, "end": None}

    # Top cities (for now just NYC)
    top_cities = [{"city_id": "nyc", "predictions": total_predictions}]

    return AnalyticsSummaryResponse(
        total_predictions=total_predictions,
        cities_served=len(cities_served),
        date_range=date_range,
        top_cities=top_cities,
    )


@router.get("/insights", response_model=AnalyticsInsightsResponse)
def insights(limit: int = Query(20, ge=1, le=100)) -> AnalyticsInsightsResponse:
    """Get insight documents from the RAG pipeline."""
    insight_docs = platform_service.get_insight_docs(limit=limit)
    return AnalyticsInsightsResponse(insights=insight_docs)


@router.get("/history", response_model=AnalyticsHistoryResponse)
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AnalyticsHistoryResponse:
    """Get recent prediction history."""
    all_history = prediction_log.get_recent_predictions(limit=limit + offset)
    paginated = all_history[offset:offset + limit]
    return AnalyticsHistoryResponse(history=paginated, limit=limit, offset=offset)


@router.get("/trends", response_model=AnalyticsTrendsResponse)
def trends(
    period: str = Query("24h", description="Period: 24h, 7d, 30d"),
) -> AnalyticsTrendsResponse:
    """Get trend data for dashboard charts."""
    history = prediction_log.get_recent_predictions(limit=5000)

    # Group by hour for the last 24h
    now = datetime.utcnow()
    if period == "24h":
        cutoff = now - timedelta(hours=24)
        granularity = "hour"
    elif period == "7d":
        cutoff = now - timedelta(days=7)
        granularity = "day"
    elif period == "30d":
        cutoff = now - timedelta(days=30)
        granularity = "day"
    else:
        cutoff = now - timedelta(hours=24)
        granularity = "hour"

    # Aggregate predictions by time bucket
    buckets = {}
    for h in history:
        ts_str = h.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            continue
        if ts < cutoff:
            continue

        if granularity == "hour":
            key = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        else:
            key = ts.date().isoformat()

        if key not in buckets:
            buckets[key] = {"count": 0, "fares": [], "distances": []}
        buckets[key]["count"] += 1
        resp = h.get("response", {})
        if isinstance(resp, dict):
            fare = resp.get("fare", {}).get("value")
            if fare is not None:
                buckets[key]["fares"].append(fare)
            dist = resp.get("distance", {}).get("value")
            if dist is not None:
                buckets[key]["distances"].append(dist)

    # Build trend series
    sorted_keys = sorted(buckets.keys())
    trends = {
        "predictions": [buckets[k]["count"] for k in sorted_keys],
        "avg_fare": [sum(buckets[k]["fares"]) / len(buckets[k]["fares"]) if buckets[k]["fares"] else 0 for k in sorted_keys],
        "avg_distance": [sum(buckets[k]["distances"]) / len(buckets[k]["distances"]) if buckets[k]["distances"] else 0 for k in sorted_keys],
    }

    return AnalyticsTrendsResponse(trends=trends, period=period)