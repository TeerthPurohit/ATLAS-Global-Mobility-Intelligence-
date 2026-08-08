"""External data-source adapter contract (ADR-008).

One method, not fetch/validate/normalize/enrich/publish: every adapter here
makes a single small, cacheable, point-lookup HTTP call (weather for one
lat/lon, holiday for one date, a route for one origin/destination pair) --
never a table scan, never a warehouse write-back (rule 8 -- a live weather
reading is used at request time and never backfilled into a mart).
validate/normalize are private helpers inside `fetch()`, not separate public
steps, because there's exactly one caller and no persistent connection to
manage.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.predictors.base import PredictionResult


class DataSourceAdapter(Protocol):
    def fetch(self, lat: float, lon: float, at: datetime) -> PredictionResult: ...
