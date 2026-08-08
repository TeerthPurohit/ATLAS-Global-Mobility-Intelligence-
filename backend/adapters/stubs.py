"""Honest stubs for data sources that need a paid API this project has $0
budget for (ADR-008). Each returns `basis="unavailable"` with a real reason
string, never a fabricated number or a silent `TODO` -- Phase 3 swaps these
implementations in behind the same signature once a budget exists; nothing
upstream (predictors, journey_service) has to change.
"""
from __future__ import annotations

from datetime import datetime

from backend.predictors.base import PredictionResult


def fetch_traffic(lat: float, lon: float, at: datetime) -> PredictionResult:
    return PredictionResult(
        value=None, unit=None, basis="unavailable", source="not_configured",
        reason="live traffic requires a paid API (Google/TomTom/HERE) -- not budgeted; "
        "see ADR-008. Historical traffic (avg_speed_mph) is used instead where available.",
    )


def fetch_events(lat: float, lon: float, at: datetime) -> PredictionResult:
    return PredictionResult(
        value=None, unit=None, basis="unavailable", source="not_configured",
        reason="events-based demand signal requires a paid API (PredictHQ/Ticketmaster) -- "
        "not budgeted; see ADR-008.",
    )


def fetch_airport_arrivals(lat: float, lon: float, at: datetime) -> PredictionResult:
    return PredictionResult(
        value=None, unit=None, basis="unavailable", source="not_configured",
        reason="airport-arrivals demand signal requires a paid API (aviationstack/FlightAware) "
        "-- not budgeted; see ADR-008.",
    )
