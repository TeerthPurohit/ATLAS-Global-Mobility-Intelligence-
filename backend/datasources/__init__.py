"""Mobility data source. One implementation, for the one city this platform
serves (ADR-013) -- `get_datasource()` stays as the single accessor so
callers keep one seam to swap if a second source ever lands.
"""
from __future__ import annotations

from backend.datasources.nyc_tlc import NYCTLCDataSource

_DATASOURCE = NYCTLCDataSource()


def get_datasource():
    return _DATASOURCE
