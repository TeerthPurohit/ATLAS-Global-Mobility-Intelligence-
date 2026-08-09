"""Global Geography Registry Service (Phase 1).

Resolves arbitrary global places (cities, administrative divisions, airports,
stations, metros) dynamically from registered seeds, GeoNames, and Google Places,
separating global geography from mobility data availability and modeling capabilities.
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.registry import cities as cities_registry  # noqa: E402
from backend.services import geonames_service  # noqa: E402

logger = logging.getLogger(__name__)

# Standard country code -> currency mapping (standard ISO 4217, data-driven).
_COUNTRY_CURRENCIES: dict[str, str] = {
    "US": "USD",
    "GB": "GBP",
    "IN": "INR",
    "AE": "AED",
    "ZA": "ZAR",
    "JP": "JPY",
    "KR": "KRW",
    "SG": "SGD",
    "DE": "EUR",
    "FR": "EUR",
    "NL": "EUR",
    "ES": "EUR",
    "IT": "EUR",
    "CA": "CAD",
    "AU": "AUD",
    "BR": "BRL",
    "AR": "ARS",
    "MX": "MXN",
    "EG": "EGP",
    "TR": "TRY",
    "SA": "SAR",
    "QA": "QAR",
    "KE": "KES",
    "TH": "THB",
    "ID": "IDR",
    "PH": "PHP",
}


def get_currency_for_country(country_code: str | None) -> str:
    if not country_code:
        return "USD"
    return _COUNTRY_CURRENCIES.get(country_code.upper(), "USD")


def _classify_place_type(fcl: str | None, fcode: str | None) -> str:
    if fcode in ("PCLI", "PCLD", "PCLF"):
        return "country"
    if fcode in ("ADM1", "ADM2", "ADM3"):
        return "administrative_division"
    if fcode == "AIRP":
        return "airport"
    if fcode in ("RSTN", "STN"):
        return "station"
    if fcl == "P":
        return "city"
    return "place"


def resolve_mobility_availability(city_id: str | None) -> bool:
    """True iff direct observed mobility dataset exists (e.g. NYC, London)."""
    if not city_id:
        return False
    city = cities_registry.get_city(city_id)
    if not city:
        return False
    caps = cities_registry.get_capabilities(city_id) or {}
    return caps.get("demand", False) or caps.get("area_analysis", False)


def resolve_modeling_availability(population: int | None, latitude: float | None) -> bool:
    """True iff cross-city modeling estimates are actually possible.
    `estimation_service.estimate_city_demand` hard-requires a population
    covariate (latitude alone isn't enough for it to return a number) --
    this used to say `population is not None or latitude is not None`,
    which claimed modeling was available for any resolvable place on Earth
    (nearly all of them have a latitude) even when population was null,
    silently overclaiming a capability the backend would then refuse."""
    return population is not None and population > 0


def get_city_profile(city_id: str) -> dict | None:
    """Phase 3: Fetch authoritative geographic facts for a city_id or geoname_id."""
    # Check registered cities first
    registered = cities_registry.get_city(city_id)
    if registered:
        capabilities = cities_registry.get_capabilities(city_id) or {}
        return {
            "city_id": registered["id"],
            "city": registered["name"],
            "country": registered.get("country_code"),
            "country_code": registered.get("country_code"),
            "coordinates": {
                "latitude": registered.get("latitude"),
                "longitude": registered.get("longitude"),
            },
            "timezone": registered.get("timezone", "UTC"),
            "currency": registered.get("currency", "USD"),
            "population": registered.get("population"),
            "administrative_hierarchy": [
                {"name": registered["name"], "type": "city"},
                {"name": registered.get("country_code"), "type": "country"},
            ],
            "alternate_names": [registered["name"]],
            "geographic_classification": {
                "feature_class": "P",
                "feature_code": "PPL",  # generic "populated place" -- a real per-city GeoNames
                                         # feature code (e.g. PPLC for a capital) was never looked
                                         # up for these seeded rows, so this doesn't claim one.
                "place_type": "city",
            },
            "capabilities": {
                "geographic": True,
                "context": True,
                "observed_mobility": capabilities.get("demand", False),
                "cross_city_model": resolve_modeling_availability(registered.get("population"), registered.get("latitude")),
            },
        }

    # Search via GeoNames by ID if numeric or search by string name
    geoname_id = None
    if city_id.isdigit():
        geoname_id = int(city_id)

    raw_hierarchy = None
    if geoname_id:
        try:
            raw_hierarchy = geonames_service.get_hierarchy(geoname_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("GeoNames hierarchy failed for id %s: %s", geoname_id, exc)

    if not raw_hierarchy:
        # Search by place name
        places = geonames_service.search_places(city_id)
        if not places:
            return None
        place = places[0]
        geoname_id = place.get("geoname_id")
        if geoname_id:
            try:
                raw_hierarchy = geonames_service.get_hierarchy(geoname_id)
            except Exception:  # noqa: BLE001
                raw_hierarchy = []

    if not geoname_id and not places:
        return None

    leaf = raw_hierarchy[-1] if raw_hierarchy else places[0]
    lat = geonames_service._num(leaf.get("latitude")) or geonames_service._num(leaf.get("lat"))
    lng = geonames_service._num(leaf.get("longitude")) or geonames_service._num(leaf.get("lng"))

    country_code = leaf.get("country_code") or leaf.get("countryCode")
    country_name = leaf.get("country_name") or leaf.get("countryName")
    population = leaf.get("population")

    tz_id = "UTC"
    if lat is not None and lng is not None:
        try:
            tz = geonames_service.get_timezone(lat, lng)
            tz_id = tz.get("timezone_id") or "UTC"
        except Exception:  # noqa: BLE001
            pass

    hierarchy_nodes = []
    if raw_hierarchy:
        for n in raw_hierarchy:
            hierarchy_nodes.append({
                "name": n.get("name"),
                "type": _classify_place_type(n.get("feature_class"), n.get("feature_code")),
            })

    place_name = leaf.get("name") or city_id.title()
    currency = get_currency_for_country(country_code)

    return {
        "city_id": str(geoname_id) if geoname_id else city_id.lower().replace(" ", "-"),
        "city": place_name,
        "country": country_name or country_code,
        "country_code": country_code,
        "coordinates": {"latitude": lat, "longitude": lng},
        "timezone": tz_id,
        "currency": currency,
        "population": population,
        "administrative_hierarchy": hierarchy_nodes,
        "alternate_names": [place_name],
        "geographic_classification": {
            "feature_class": leaf.get("feature_class") or leaf.get("fcl"),
            "feature_code": leaf.get("feature_code") or leaf.get("fcode"),
            "place_type": _classify_place_type(leaf.get("feature_class"), leaf.get("feature_code")),
        },
        "capabilities": {
            "geographic": True,
            "context": True,
            "observed_mobility": False,
            "cross_city_model": resolve_modeling_availability(population, lat),
        },
    }


def search_cities(query: str, limit: int = 10, country_code: str | None = None) -> list[dict]:
    """Phase 2: Global city search API backing GET /api/geography/search."""
    query_clean = query.strip()
    if not query_clean:
        return []

    results = []
    seen_ids = set()

    # Check registered cities first
    for city in cities_registry.list_cities(country_code=country_code):
        if query_clean.lower() in city["name"].lower() or query_clean.lower() == city["id"]:
            caps = cities_registry.get_capabilities(city["id"]) or {}
            results.append({
                "id": city["id"],
                "name": city["name"],
                "country": city["country_code"],
                "country_code": city["country_code"],
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "timezone": city["timezone"],
                "population": city.get("population"),
                "place_type": "city",
                "mobility_available": caps.get("demand", False) or caps.get("area_analysis", False),
                "modeling_available": True,
            })
            seen_ids.add(city["id"])

    # Search GeoNames places. Only include ones GeoNames actually gives a
    # population for -- estimation_service.estimate_city_demand hard-requires
    # a population covariate, so a result without one is a dead end (real
    # geography, but no honest demand/fare estimate possible) rather than a
    # usable "modeled" city. Was previously letting every GeoNames hit
    # through with modeling_available hardcoded True regardless.
    raw_places = geonames_service.search_places(query_clean, country=country_code)
    for p in raw_places:
        gid = str(p.get("geoname_id")) if p.get("geoname_id") else None
        if not gid or gid in seen_ids:
            continue
        population = p.get("population")
        if not population:
            continue
        seen_ids.add(gid)

        name = p.get("name") or query_clean.title()
        cc = p.get("country_code")
        cname = p.get("country_name") or cc

        results.append({
            "id": gid,
            "name": name,
            "country": cname,
            "country_code": cc,
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "timezone": None,
            "population": population,
            "place_type": _classify_place_type(p.get("feature_class"), p.get("feature_code")),
            "mobility_available": False,
            "modeling_available": True,
        })
        if len(results) >= limit:
            break

    return results[:limit]
