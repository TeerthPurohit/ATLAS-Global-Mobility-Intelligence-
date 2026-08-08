"""`MobilityDataSource` protocol (SPEC-013 FR-6) -- the shape every city's
data source implements so `backend/services/prediction_service.py` and a
future NL-to-SQL city adapter can read areas/demand/fares/flows/temporal
metrics without knowing which city they're talking to.

`get_trips()` is deliberately NOT part of this protocol (rule 8): raw trip
rows stay dbt/offline-only, never read on a live request path. Every method
here reads a pre-aggregated mart, not a raw table.
"""
from __future__ import annotations

from typing import Protocol


class MobilityDataSource(Protocol):
    city_id: str

    def get_areas(self) -> list[dict]:
        """Every area (zone/station/etc.) for this city, from its canonical
        area mart."""
        ...

    def get_demand(
        self, area_id: int | None = None, hour: int | None = None, day_of_week: int | None = None
    ) -> list[dict]:
        """Aggregated demand rows, optionally filtered by area/hour."""
        ...

    def get_fares(self, pickup_area: str | None = None, dropoff_area: str | None = None) -> list[dict]:
        """Aggregated fare-stat rows, optionally filtered by pickup/dropoff area."""
        ...

    def get_zone_flows(self, pickup_area: str | None = None) -> list[dict]:
        """Aggregated origin-destination flow rows, optionally filtered by origin."""
        ...

    def get_temporal_metrics(self, metric: str) -> list[dict]:
        """A citywide hourly series for `metric` (e.g. "demand"), for /forecast."""
        ...
