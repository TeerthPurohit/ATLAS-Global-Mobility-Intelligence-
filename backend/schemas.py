"""Pydantic request/response models for the predictions and zones routes
(FR-7). Chat schemas are added separately once rag_pipeline.py exists."""

from __future__ import annotations

from pydantic import BaseModel


class DemandPrediction(BaseModel):
    zone_id: int
    hour: int
    day_of_week: int
    predicted_demand: float
    model: str


class FarePrediction(BaseModel):
    pickup_zone: int
    dropoff_zone: int
    hour: int
    predicted_fare: float
    model: str


class Zone(BaseModel):
    zone_id: int
    zone: str
    borough: str
    service_zone: str | None = None
    latitude: float
    longitude: float

