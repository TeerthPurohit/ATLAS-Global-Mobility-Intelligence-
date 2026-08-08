"""Geography Discovery API -- world -> country -> city search -> place
hierarchy, backed by GeoNames with a Google Places fallback for search
(backend/services/geonames_service.py, google_places_service.py).

Additive and isolated: does not touch the existing NYC TLC zone/prediction/
RAG stack. `backend/services/geography_service.py`'s lat/lon -> zone_id
resolver and the `/zones` router are unaffected. `mobility_support` on a
result is checked against `backend/registry/cities.py` (SPEC-013's real
city registry, `dbt_project/seeds/cities.csv`) -- the single source of
truth for "which cities does this platform actually support," not a second,
disconnected map. GeoNames has no `city_id` concept of its own, so a small
local geoname_id -> city_id identity link is still needed (that mapping has
no natural home in the cities seed), but whether the city_id it points to
is real is always re-checked against the live registry, not trusted from
this dict alone -- a stale/removed city_id here degrades to unsupported
rather than lying.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.errors_geography import GeographyError, GeographyErrorCode
from backend.registry import cities as cities_registry
from backend.registry import countries as countries_registry
from backend.schemas_geography import (
    ChildPlace,
    CityContextResponse,
    CityProfileResponse,
    CountriesResponse,
    Country,
    GlobalCitySearchResponse,
    GlobalCitySearchResult,
    HierarchyNode,
    HierarchyPlace,
    HierarchyResponse,
    MobilitySupport,
    PlaceSearchResult,
    PlacesResponse,
    ReverseGeoResponse,
    SearchResponse,
)
from backend.services import geonames_service

router = APIRouter(prefix="/api/geography", tags=["Geography Discovery"])

# New York City's well-known GeoNames ID -- GeoNames has no city_id of its
# own, so this identity link is maintained here; a second city adds its own
# geoname_id -> city_id entry once it's onboarded (dbt_project/seeds/cities.csv).
_NYC_GEONAME_ID = 5128581
_GEONAME_ID_TO_CITY_ID: dict[int, str] = {_NYC_GEONAME_ID: "nyc"}


def _mobility_support(geoname_id: int | None) -> MobilitySupport:
    city_id = _GEONAME_ID_TO_CITY_ID.get(geoname_id) if geoname_id else None
    if city_id is not None and cities_registry.get_city(city_id) is None:
        city_id = None  # this dict's mapping is stale -- the registry is the source of truth
    return MobilitySupport(supported=city_id is not None, city_id=city_id)


def _classify_feature(fcl: str | None) -> str:
    if fcl == "A":
        return "administrative_division"
    if fcl == "P":
        return "populated_place"
    return "other"


def _hierarchy_type(fcl: str | None, fcode: str | None) -> str:
    if fcode == "CONT":
        return "continent"
    if fcode == "PCLI":
        return "country"
    if fcode == "ADM1":
        return "admin1"
    if fcode == "ADM2":
        return "admin2"
    if fcl == "P":
        return "city"
    return "place"


def _find_country_name(raw_hierarchy: list[dict]) -> str | None:
    for node in raw_hierarchy:
        if node.get("feature_code") == "PCLI":
            return node["name"]
    return None


@router.get(
    "/countries",
    response_model=CountriesResponse,
    summary="List all countries",
    description="Every country GeoNames knows about. `supported` reflects whether this "
    "platform has real mobility data/models for that country -- not GeoNames coverage.",
    responses={503: {"description": "GeoNames unavailable"}},
)
def list_countries() -> CountriesResponse:
    supported_iso_codes = {c["iso_code"] for c in countries_registry.list_countries() if c["supported"]}
    countries = [
        Country(
            geoname_id=c["geoname_id"],
            iso2=c["iso2"],
            iso3=c["iso3"],
            name=c["name"],
            capital=c["capital"],
            continent=c["continent"],
            latitude=c["latitude"],
            longitude=c["longitude"],
            supported=c["iso2"] in supported_iso_codes,
        )
        for c in geonames_service.get_all_countries()
    ]
    return CountriesResponse(countries=countries)


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search for a place by name",
    description="Prioritizes populated places over every GeoNames feature matching the "
    "query. Falls back to Google Places if GeoNames is unavailable or returns nothing.",
    responses={503: {"description": "Both GeoNames and the Google Places fallback are unavailable"}},
)
def search_places(
    q: str = Query(..., min_length=1, description="Place name to search for"),
    country: str | None = Query(None, description="Optional ISO-3166 country code to narrow the search"),
) -> SearchResponse:
    raw_results = geonames_service.search_places(q, country)
    results = [
        PlaceSearchResult(
            geoname_id=r.get("geoname_id"),
            name=r.get("name"),
            country_code=r.get("country_code"),
            country_name=r.get("country_name"),
            admin1_code=r.get("admin1_code"),
            admin1_name=r.get("admin1_name"),
            feature_class=r.get("feature_class"),
            feature_code=r.get("feature_code"),
            latitude=r.get("latitude"),
            longitude=r.get("longitude"),
            source=r.get("source", "geonames"),
            mobility_support=_mobility_support(r.get("geoname_id")),
        )
        for r in raw_results
    ]
    return SearchResponse(results=results)


@router.get(
    "/countries/{country_code}/places",
    response_model=PlacesResponse,
    summary="List a country's child places",
    description="GeoNames' direct children of a country (usually admin1 divisions, "
    "sometimes populated places directly). `place_type` distinguishes administrative "
    "divisions from populated places -- not every child is a city.",
    responses={404: {"description": "Unknown country code"}, 503: {"description": "GeoNames unavailable"}},
)
def country_places(country_code: str) -> PlacesResponse:
    country_code = country_code.upper()
    country_geoname_id = geonames_service.get_country_geoname_id(country_code)
    if country_geoname_id is None:
        raise GeographyError(GeographyErrorCode.COUNTRY_NOT_FOUND, f"Unknown country code: {country_code}", 404)
    raw_children = geonames_service.get_children(country_geoname_id)
    places = [
        ChildPlace(
            geoname_id=c.get("geoname_id"),
            name=c.get("name"),
            feature_class=c.get("feature_class"),
            feature_code=c.get("feature_code"),
            place_type=_classify_feature(c.get("feature_class")),
            latitude=c.get("latitude"),
            longitude=c.get("longitude"),
            population=c.get("population"),
        )
        for c in raw_children
    ]
    return PlacesResponse(country_code=country_code, places=places)


@router.get(
    "/places/{geoname_id}/hierarchy",
    response_model=HierarchyResponse,
    summary="Get a place's geographic hierarchy",
    description="Continent -> country -> admin divisions -> place, ordered top-down. "
    "Includes timezone as an optional enrichment when resolvable.",
    responses={404: {"description": "Unknown place"}, 503: {"description": "GeoNames unavailable"}},
)
def place_hierarchy(geoname_id: int) -> HierarchyResponse:
    raw = geonames_service.get_hierarchy(geoname_id)
    if not raw:
        raise GeographyError(GeographyErrorCode.PLACE_NOT_FOUND, f"Unknown place: {geoname_id}", 404)

    nodes = [
        HierarchyNode(
            geoname_id=n.get("geoname_id"),
            name=n.get("name"),
            type=_hierarchy_type(n.get("feature_class"), n.get("feature_code")),
        )
        for n in raw
    ]
    leaf = raw[-1]
    timezone = None
    if leaf.get("latitude") is not None and leaf.get("longitude") is not None:
        try:
            timezone = geonames_service.get_timezone(leaf["latitude"], leaf["longitude"]).get("timezone_id")
        except GeographyError:
            timezone = None  # optional enrichment -- hierarchy itself still succeeds

    place = HierarchyPlace(
        geoname_id=leaf.get("geoname_id"),
        name=leaf.get("name"),
        country=_find_country_name(raw),
        mobility_support=_mobility_support(leaf.get("geoname_id")),
        timezone=timezone,
    )
    return HierarchyResponse(place=place, hierarchy=nodes)


@router.get(
    "/reverse",
    response_model=ReverseGeoResponse,
    summary="Reverse-geocode a coordinate",
    description="Latitude/longitude -> country + admin1 division, for map interaction.",
    responses={400: {"description": "Coordinates out of range"}, 503: {"description": "GeoNames unavailable"}},
)
def reverse_geocode(
    lat: float = Query(..., description="Latitude, -90 to 90"),
    lng: float = Query(..., description="Longitude, -180 to 180"),
) -> ReverseGeoResponse:
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise GeographyError(
            GeographyErrorCode.INVALID_COORDINATES, "lat must be in [-90, 90] and lng in [-180, 180].", 400
        )
    data = geonames_service.reverse_country(lat, lng)
    return ReverseGeoResponse(
        country_code=data.get("country_code"),
        country_name=data.get("country_name"),
        admin1_code=data.get("admin1_code"),
        admin1_name=data.get("admin1_name"),
        latitude=lat,
        longitude=lng,
    )


# ── Global Mobility Intelligence Engine Endpoints (Phases 2 - 4) ───────────


@router.get(
    "/search/global",
    response_model=GlobalCitySearchResponse,
    summary="Phase 2 — Global City Search API",
    description="Resolves arbitrary cities globally (Mumbai, Cape Town, Dubai, Tokyo, NYC, London, etc.) "
    "returning id, name, country, coordinates, timezone, population, mobility_available, modeling_available.",
)
def search_global_cities(
    q: str = Query(..., min_length=1, description="Place or city name to search"),
    limit: int = Query(10, ge=1, le=50, description="Max results limit"),
    country: str | None = Query(None, description="Optional country code filter"),
) -> GlobalCitySearchResponse:
    from backend.services import global_geography_service

    raw_items = global_geography_service.search_cities(q, limit=limit, country_code=country)
    results = [GlobalCitySearchResult(**item) for item in raw_items]
    return GlobalCitySearchResponse(results=results)


@router.get(
    "/{city_id}",
    response_model=CityProfileResponse,
    summary="Phase 3 — City Profile API",
    description="Authoritative geographic facts for any resolved city/place. "
    "Zero fabricated mobility statistics.",
    responses={404: {"description": "City or place not found"}},
)
def get_city_profile(city_id: str) -> CityProfileResponse:
    from backend.services import global_geography_service

    profile = global_geography_service.get_city_profile(city_id)
    if not profile:
        raise GeographyError(
            GeographyErrorCode.PLACE_NOT_FOUND, f"Unknown or unresolvable city_id: {city_id!r}", 404
        )
    return CityProfileResponse(**profile)


@router.get(
    "/{city_id}/context",
    response_model=CityContextResponse,
    summary="Phase 4 — Context Orchestrator API",
    description="Backend context engine querying environmental facts (geography, weather, "
    "calendar, urban density, routing capability) with standardized provenance envelopes.",
)
def get_city_context(city_id: str) -> CityContextResponse:
    from backend.services import context_orchestrator

    context_data = context_orchestrator.get_city_context(city_id)
    return CityContextResponse(**context_data)
