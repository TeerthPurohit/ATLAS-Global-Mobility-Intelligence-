"""GeoNames JSON web services client -- the geography-discovery layer's
source of truth for world/country/city data (additive; does not touch the
existing NYC TLC zone implementation, see backend/services/geography_service.py
for that).

Two things worth knowing before you touch this file:

1. Auth is `username` only. GeoNames' free API has no password parameter in
   any request -- GEONAMES_PASSWORD (account login, not an API credential)
   is intentionally never read here.
2. `https://api.geonames.org` does not present a valid TLS certificate on
   the free tier (confirmed independently -- other HTTPS hosts work fine
   from this environment). `http://` is what GeoNames' own official client
   libraries use for the free endpoint; this isn't a downgrade introduced
   here, it's what actually works.

Every call degrades honestly on failure (ADR-008 pattern): auth/rate-limit/
network/parse failures raise a typed GeographyError with a generic message,
never a fabricated result and never a raw GeoNames error string (which could
hint at account configuration). Successful lookups are cached in-process
with lru_cache -- country/place/timezone data doesn't change during a
process lifetime, matching the adapters/ caching convention (no Redis,
single free-tier host, see ADR-008).
"""
from __future__ import annotations

import os
from functools import lru_cache

import httpx

from backend.errors_geography import GeographyError, GeographyErrorCode
from backend.services import google_places_service

_USERNAME = os.environ.get("GEONAMES_USERNAME", "")
_BASE_URL = "http://api.geonames.org"
_TIMEOUT = 5.0

# GeoNames' own status.value codes (geonames.org/export/webservice-exception.html).
_AUTH_CODES = {10, 11, 12, 13, 14, 15, 16, 17, 21, 22}
_RATE_LIMIT_CODES = {18, 19, 20}

_UNAVAILABLE_MESSAGE = "Geographic discovery is temporarily unavailable."


def _num(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _get(path: str, params: dict) -> dict:
    if not _USERNAME:
        raise GeographyError(GeographyErrorCode.GEONAMES_UNAVAILABLE, _UNAVAILABLE_MESSAGE, 503)
    try:
        resp = httpx.get(f"{_BASE_URL}/{path}", params={**params, "username": _USERNAME}, timeout=_TIMEOUT)
        # Deliberately no resp.raise_for_status(): GeoNames returns its own
        # machine-readable {"status": {...}} error body alongside a non-2xx
        # HTTP status (confirmed live -- an auth failure is HTTP 401 *with* a
        # parseable JSON body), so the JSON body is parsed first and is what
        # drives error classification below, not the HTTP status code alone.
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 -- network/timeout/non-JSON body degrades honestly
        raise GeographyError(GeographyErrorCode.GEONAMES_UNAVAILABLE, _UNAVAILABLE_MESSAGE, 503) from exc

    if isinstance(data, dict) and "status" in data:
        code = data["status"].get("value")
        if code in _AUTH_CODES:
            raise GeographyError(GeographyErrorCode.GEONAMES_AUTH_FAILED, _UNAVAILABLE_MESSAGE, 503)
        if code in _RATE_LIMIT_CODES:
            raise GeographyError(
                GeographyErrorCode.GEONAMES_RATE_LIMITED,
                "Geographic discovery is temporarily busy, please retry shortly.", 503,
            )
        raise GeographyError(GeographyErrorCode.GEONAMES_UNAVAILABLE, _UNAVAILABLE_MESSAGE, 503)
    return data


def _normalize_place(row: dict, source: str) -> dict:
    return {
        "geoname_id": row.get("geonameId"),
        "name": row.get("name") or row.get("toponymName"),
        "country_code": row.get("countryCode"),
        "country_name": row.get("countryName"),
        "admin1_code": row.get("adminCode1"),
        "admin1_name": row.get("adminName1"),
        "feature_class": row.get("fcl"),
        "feature_code": row.get("fcode"),
        "latitude": _num(row.get("lat")),
        "longitude": _num(row.get("lng")),
        "source": source,
    }


@lru_cache(maxsize=1)
def get_all_countries() -> list[dict]:
    data = _get("countryInfoJSON", {})
    rows = data.get("geonames", []) if isinstance(data, dict) else []
    result = []
    for r in rows:
        north, south = _num(r.get("north")), _num(r.get("south"))
        east, west = _num(r.get("east")), _num(r.get("west"))
        # GeoNames gives a mainland bounding box, not a single point -- the
        # bbox midpoint is a real geometric derivation from real data, not a
        # fabricated coordinate.
        result.append(
            {
                "geoname_id": r.get("geonameId"),
                "iso2": r.get("countryCode"),
                "iso3": r.get("isoAlpha3"),
                "name": r.get("countryName"),
                "capital": r.get("capital"),
                "continent": r.get("continent"),
                "latitude": (north + south) / 2 if north is not None and south is not None else None,
                "longitude": (east + west) / 2 if east is not None and west is not None else None,
            }
        )
    return result


def get_country_geoname_id(iso2: str) -> int | None:
    for c in get_all_countries():
        if c["iso2"] == iso2:
            return c["geoname_id"]
    return None


@lru_cache(maxsize=256)
def _search_geonames_cached(q: str, country: str | None) -> tuple[dict, ...]:
    params: dict = {"q": q, "featureClass": "P", "isNameRequired": "true", "style": "MEDIUM", "maxRows": 15}
    if country:
        params["country"] = country
    data = _get("searchJSON", params)
    rows = data.get("geonames", []) if isinstance(data, dict) else []
    return tuple(_normalize_place(r, source="geonames") for r in rows)


def search_places(q: str, country: str | None = None) -> list[dict]:
    """Prioritizes populated places (GeoNames featureClass=P) over every
    matching feature. Falls back to Google Places only when GeoNames itself
    errors or returns nothing -- see google_places_service.search()."""
    try:
        results = list(_search_geonames_cached(q, country))
        if results:
            return results
    except GeographyError:
        pass
    return google_places_service.search(q, country)


@lru_cache(maxsize=256)
def get_children(geoname_id: int) -> list[dict]:
    data = _get("childrenJSON", {"geonameId": geoname_id, "maxRows": 500})
    rows = data.get("geonames", []) if isinstance(data, dict) else []
    return [
        {
            "geoname_id": r.get("geonameId"),
            "name": r.get("name"),
            "feature_class": r.get("fcl"),
            "feature_code": r.get("fcode"),
            "latitude": _num(r.get("lat")),
            "longitude": _num(r.get("lng")),
            "population": r.get("population"),
        }
        for r in rows
    ]


@lru_cache(maxsize=256)
def get_hierarchy(geoname_id: int) -> list[dict]:
    data = _get("hierarchyJSON", {"geonameId": geoname_id})
    rows = data.get("geonames", []) if isinstance(data, dict) else []
    return [
        {
            "geoname_id": r.get("geonameId"),
            "name": r.get("name"),
            "feature_class": r.get("fcl"),
            "feature_code": r.get("fcode"),
            "latitude": _num(r.get("lat")),
            "longitude": _num(r.get("lng")),
        }
        for r in rows
    ]


@lru_cache(maxsize=512)
def _reverse_country_cached(lat: float, lng: float) -> dict:
    data = _get("countryCodeJSON", {"lat": lat, "lng": lng, "type": "JSON"})
    if not data.get("countryCode"):
        return {"country_code": None, "country_name": None, "admin1_code": None, "admin1_name": None}
    return {
        "country_code": data.get("countryCode"),
        "country_name": data.get("countryName"),
        "admin1_code": data.get("adminCode1"),
        "admin1_name": data.get("adminName1"),
    }


def reverse_country(lat: float, lng: float) -> dict:
    # ~1km buckets so nearby map clicks share one upstream call.
    return _reverse_country_cached(round(lat, 2), round(lng, 2))


@lru_cache(maxsize=512)
def _get_timezone_cached(lat: float, lng: float) -> dict:
    data = _get("timezoneJSON", {"lat": lat, "lng": lng})
    return {"timezone_id": data.get("timezoneId")}


def get_timezone(lat: float, lng: float) -> dict:
    return _get_timezone_cached(round(lat, 2), round(lng, 2))
