"""Analytics APIs (Part 13 of API Decomposition).

Frontend dashboard analytics operating on prediction logs/warehouse data.

All aggregations read the real columns of the SQLite prediction log
(`prediction_log.get_recent_predictions`): `requested_at` (aware UTC ISO
string) for time bucketing and `response_json` (a JSON string of the full
JourneyEstimate) for fare/distance/city extraction. Every timestamp is kept
timezone-aware so bucketing never compares naive against aware datetimes.
"""
from __future__ import annotations  # noqa: I001

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Query
from loguru import logger

# Add repo root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.schemas import (
    AnalyticsHistoryResponse,
    AnalyticsInsightsResponse,
    AnalyticsSummaryResponse,
    AnalyticsTrendsResponse,
)
from backend.services import platform_service, prediction_log

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

_HISTORY_SCAN_LIMIT = 10000


def _parse_requested_at(raw: str | None) -> datetime | None:
    """Parse a log `requested_at` ISO string into an aware UTC datetime.
    The log always writes `datetime.now(timezone.utc).isoformat()`, but old
    rows / naive variants are tolerated: a naive timestamp is assumed UTC."""
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _response_payload(row: dict) -> dict:
    """Unwrap the stored `response_json` column into a dict, tolerating a
    legacy row that stored the response object directly under `response`."""
    raw = row.get("response_json")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def summary() -> AnalyticsSummaryResponse:
    """Analytics summary from real prediction log rows."""
    logger.info("GET /api/analytics/summary step=start")
    history = prediction_log.get_recent_predictions(limit=_HISTORY_SCAN_LIMIT)
    total_predictions = len(history)

    cities: dict[str, int] = {}
    parsed_dates = []
    for h in history:
        city_id = h.get("city_id")
        if not city_id:
            city_id = _response_payload(h).get("city_id")
        if city_id:
            cities[city_id] = cities.get(city_id, 0) + 1
        ts = _parse_requested_at(h.get("requested_at"))
        if ts is not None:
            parsed_dates.append(ts)

    date_range = {"start": None, "end": None}
    if parsed_dates:
        date_range = {
            "start": min(parsed_dates).isoformat(),
            "end": max(parsed_dates).isoformat(),
        }

    top_cities = [
        {"city_id": city_id, "predictions": count}
        for city_id, count in sorted(cities.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ]

    logger.info("GET /api/analytics/summary step=done total_predictions={} cities_served={}", total_predictions, len(cities))
    return AnalyticsSummaryResponse(
        total_predictions=total_predictions,
        cities_served=len(cities),
        date_range=date_range,
        top_cities=top_cities,
    )


@router.get("/insights", response_model=AnalyticsInsightsResponse)
def insights(limit: int = Query(20, ge=1, le=100)) -> AnalyticsInsightsResponse:
    """Get insight documents from the RAG pipeline."""
    logger.info("GET /api/analytics/insights step=start limit={}", limit)
    insight_docs = platform_service.get_insight_docs(limit=limit)
    logger.info("GET /api/analytics/insights step=done count={}", len(insight_docs))
    return AnalyticsInsightsResponse(insights=insight_docs)


@router.get("/history", response_model=AnalyticsHistoryResponse)
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AnalyticsHistoryResponse:
    """Get recent prediction history."""
    logger.info("GET /api/analytics/history step=start limit={} offset={}", limit, offset)
    all_history = prediction_log.get_recent_predictions(limit=limit + offset)
    paginated = all_history[offset:offset + limit]
    logger.info("GET /api/analytics/history step=done returned={}", len(paginated))
    return AnalyticsHistoryResponse(history=paginated, limit=limit, offset=offset)


@router.get("/trends", response_model=AnalyticsTrendsResponse)
def trends(
    period: str = Query("24h", description="Period: 24h, 7d, 30d"),
) -> AnalyticsTrendsResponse:
    """Real trend series bucketed from log timestamps and response payloads.
    `now` and every log timestamp are aware UTC -- no naive/aware mix."""
    logger.info("GET /api/analytics/trends step=start period={}", period)
    history = prediction_log.get_recent_predictions(limit=_HISTORY_SCAN_LIMIT)

    now = datetime.now(timezone.utc)
    if period == "7d":
        cutoff = now - timedelta(days=7)
        granularity = "day"
    elif period == "30d":
        cutoff = now - timedelta(days=30)
        granularity = "day"
    else:  # 24h default
        cutoff = now - timedelta(hours=24)
        granularity = "hour"

    buckets: dict[str, dict] = {}
    for h in history:
        ts = _parse_requested_at(h.get("requested_at"))
        if ts is None or ts < cutoff:
            continue

        key = ts.replace(minute=0, second=0, microsecond=0).isoformat() if granularity == "hour" else ts.date().isoformat()
        bucket = buckets.setdefault(key, {"count": 0, "fares": [], "distances": []})
        bucket["count"] += 1

        payload = _response_payload(h)
        fare = payload.get("fare", {}).get("value") if isinstance(payload.get("fare"), dict) else None
        distance = payload.get("distance", {}).get("value") if isinstance(payload.get("distance"), dict) else None
        if fare is not None:
            bucket["fares"].append(float(fare))
        if distance is not None:
            bucket["distances"].append(float(distance))

    sorted_keys = sorted(buckets.keys())
    logger.info("GET /api/analytics/trends step=done period={} buckets={}", period, len(sorted_keys))
    return AnalyticsTrendsResponse(
        trends={
            "predictions": [buckets[k]["count"] for k in sorted_keys],
            "avg_fare": [sum(buckets[k]["fares"]) / len(buckets[k]["fares"]) if buckets[k]["fares"] else 0.0 for k in sorted_keys],
            "avg_distance": [sum(buckets[k]["distances"]) / len(buckets[k]["distances"]) if buckets[k]["distances"] else 0.0 for k in sorted_keys],
        },
        period=period,
    )
