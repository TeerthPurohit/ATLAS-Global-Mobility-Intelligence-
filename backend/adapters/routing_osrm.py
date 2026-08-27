"""Real road-network routing via OSRM (ADR-008).

Defaults to OSRM's public demo server (`OSRM_URL` env var overrides it for
a self-hosted instance) -- a real routing engine over real OpenStreetMap
road data, not a haversine guess. `basis="unavailable"` on any failure; the
caller (journey_service.py) falls back to the haversine straight-line
distance already used by `model_service.py`, which is honestly labeled as
straight-line rather than road distance, never silently swapped in as if it
were the same thing.

Self-hosting via docker-compose (matching the existing Qdrant service
pattern) is the production upgrade path -- not done in this pass, since it
requires downloading and preprocessing an OSM extract, a genuinely separate
infra task. The public demo server is real, free, and sufficient to prove
the integration end-to-end.
"""
from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache

import httpx
from loguru import logger

from backend.predictors.base import PredictionResult

_OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")


@lru_cache(maxsize=512)
def _cached_route(pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float) -> dict | None:
    url = f"{_OSRM_URL}/route/v1/driving/{pickup_lon},{pickup_lat};{dropoff_lon},{dropoff_lat}"
    try:
        resp = httpx.get(url, params={"overview": "false", "alternatives": "false"}, timeout=4.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("routing_osrm step=route no_route code={}", data.get("code"))
            return None
        route = data["routes"][0]
        return {"distance_m": route["distance"], "duration_s": route["duration"]}
    except Exception as exc:  # noqa: BLE001
        logger.warning("routing_osrm step=route failed url={} reason={}", url, exc)
        return None


def fetch_distance(pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float) -> PredictionResult:
    route = _cached_route(round(pickup_lat, 5), round(pickup_lon, 5), round(dropoff_lat, 5), round(dropoff_lon, 5))
    if route is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="osrm",
            reason="OSRM route request failed or returned no route",
        )
    return PredictionResult(
        value=round(route["distance_m"] / 1609.344, 2), unit="miles", basis="computed", source="osrm", reason=None,
    )


def fetch_duration(pickup_lat: float, pickup_lon: float, dropoff_lat: float, dropoff_lon: float) -> PredictionResult:
    route = _cached_route(round(pickup_lat, 5), round(pickup_lon, 5), round(dropoff_lat, 5), round(dropoff_lon, 5))
    if route is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="osrm",
            reason="OSRM route request failed or returned no route",
        )
    return PredictionResult(
        value=round(route["duration_s"] / 60.0, 1), unit="minutes", basis="computed", source="osrm", reason=None,
    )


def fetch(lat: float, lon: float, at: datetime) -> PredictionResult:  # pragma: no cover -- DataSourceAdapter shape
    raise NotImplementedError("routing_osrm exposes fetch_distance/fetch_duration (two coordinates), not fetch()")
