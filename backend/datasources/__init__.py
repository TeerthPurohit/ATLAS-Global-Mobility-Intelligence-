"""Per-city mobility data source registry (SPEC-013 FR-6). One real entry
today (`nyc`); a second city registers here with its own `MobilityDataSource`
implementation, zero changes to callers of `get_datasource()`.
"""
from __future__ import annotations

from backend.datasources.nyc_tlc import NYCTLCDataSource

_DATASOURCES = {"nyc": NYCTLCDataSource()}


def get_datasource(city_id: str):
    return _DATASOURCES.get(city_id)
