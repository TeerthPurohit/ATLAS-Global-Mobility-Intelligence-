"""Google Places fallback for city/place search -- used only when GeoNames
search fails or is unavailable (backend/services/geonames_service.py's
search_places()). Text Search (New) endpoint returns name/lat-lng/country in
one call, no separate Place Details round trip needed.

This is a fallback source, not a peer to GeoNames: any failure here degrades
to an empty result list rather than raising, since the caller's own
GEONAMES_UNAVAILABLE path is the honest error state, not this.
"""
from __future__ import annotations

import os

import httpx
from loguru import logger

_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
_URL = "https://places.googleapis.com/v1/places:searchText"
_TIMEOUT = 5.0
_FIELD_MASK = "places.displayName,places.location,places.addressComponents"


def _address_components(place: dict) -> dict[str, dict]:
    by_type: dict[str, dict] = {}
    for component in place.get("addressComponents", []):
        for t in component.get("types", []):
            by_type.setdefault(t, component)
    return by_type


def search(q: str, country: str | None = None) -> list[dict]:
    if not _API_KEY:
        logger.debug("google_places_service.search step=skip reason=no_api_key")
        return []
    text_query = f"{q}, {country}" if country else q
    try:
        resp = httpx.post(
            _URL,
            json={"textQuery": text_query},
            headers={
                "X-Goog-Api-Key": _API_KEY,
                "X-Goog-FieldMask": _FIELD_MASK,
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 -- fallback source; degrade to empty, never raise
        logger.warning("google_places_service.search step=request failed q={!r} reason={}", q, exc)
        return []

    results = []
    for place in data.get("places", []):
        components = _address_components(place)
        location = place.get("location") or {}
        results.append(
            {
                "geoname_id": None,
                "name": (place.get("displayName") or {}).get("text"),
                "country_code": (components.get("country") or {}).get("shortText"),
                "country_name": (components.get("country") or {}).get("longText"),
                "admin1_code": None,
                "admin1_name": (components.get("administrative_area_level_1") or {}).get("longText"),
                "feature_class": None,
                "feature_code": None,
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "source": "google_places",
            }
        )
    return results
