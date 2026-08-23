"""Per-city mobility data source registry. Each city registers here with its
own data-source implementation, zero changes to callers of
`get_datasource()`.
"""
from __future__ import annotations

from backend.datasources.nyc_tlc import NYCTLCDataSource

_DATASOURCES = {"nyc": NYCTLCDataSource()}


def get_datasource(city_id: str):
    return _DATASOURCES.get(city_id)
