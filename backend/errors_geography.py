"""Error taxonomy for the geography-discovery layer (GeoNames + Google Places
fallback). Mirrors backend/adapters/'s honest-degrade pattern (ADR-008):
callers never see a raw exception, a raw GeoNames error string, or a leaked
credential -- only one of these typed errors with a safe, generic message.
"""
from __future__ import annotations

from enum import Enum


class GeographyErrorCode(str, Enum):
    GEONAMES_UNAVAILABLE = "GEONAMES_UNAVAILABLE"
    GEONAMES_AUTH_FAILED = "GEONAMES_AUTH_FAILED"
    GEONAMES_RATE_LIMITED = "GEONAMES_RATE_LIMITED"
    PLACE_NOT_FOUND = "PLACE_NOT_FOUND"
    COUNTRY_NOT_FOUND = "COUNTRY_NOT_FOUND"
    INVALID_COORDINATES = "INVALID_COORDINATES"


class GeographyError(Exception):
    def __init__(self, code: GeographyErrorCode, message: str, status_code: int = 502):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
