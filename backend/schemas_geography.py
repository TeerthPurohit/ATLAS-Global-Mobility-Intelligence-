"""Pydantic response models for the geography-discovery layer (GeoNames +
Google Places fallback). Deliberately separate from backend/schemas.py --
this is an additive, isolated discovery layer (world -> country -> city
search -> hierarchy), not part of the existing NYC prediction/zone schema.
"""
from __future__ import annotations

from pydantic import BaseModel


class MobilitySupport(BaseModel):
    """GeoNames tells us a place exists; this tells us whether OUR mobility
    intelligence system has real data/models for it -- never fabricated."""

    supported: bool
    city_id: str | None = None


class Country(BaseModel):
    geoname_id: int | None
    iso2: str | None
    iso3: str | None
    name: str | None
    capital: str | None
    continent: str | None
    latitude: float | None
    longitude: float | None
    supported: bool


class CountriesResponse(BaseModel):
    countries: list[Country]


class PlaceSearchResult(BaseModel):
    geoname_id: int | None
    name: str | None
    country_code: str | None
    country_name: str | None
    admin1_code: str | None
    admin1_name: str | None
    feature_class: str | None
    feature_code: str | None
    latitude: float | None
    longitude: float | None
    source: str
    mobility_support: MobilitySupport


class SearchResponse(BaseModel):
    results: list[PlaceSearchResult]


class ChildPlace(BaseModel):
    geoname_id: int | None
    name: str | None
    feature_class: str | None
    feature_code: str | None
    place_type: str
    latitude: float | None
    longitude: float | None
    population: int | None


class PlacesResponse(BaseModel):
    country_code: str
    places: list[ChildPlace]


class HierarchyNode(BaseModel):
    geoname_id: int | None
    name: str | None
    type: str


class HierarchyPlace(BaseModel):
    geoname_id: int | None
    name: str | None
    country: str | None
    mobility_support: MobilitySupport
    timezone: str | None = None


class HierarchyResponse(BaseModel):
    place: HierarchyPlace
    hierarchy: list[HierarchyNode]


class ReverseGeoResponse(BaseModel):
    country_code: str | None
    country_name: str | None
    admin1_code: str | None
    admin1_name: str | None
    latitude: float
    longitude: float


# ── Global Mobility Engine Schemas (Phases 1 - 4) ──────────────────────────


class GlobalPlace(BaseModel):
    global_place_id: str
    source: str
    source_id: str | int | None = None
    name: str
    ascii_name: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    admin1: str | None = None
    admin2: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    population: int | None = None
    timezone: str | None = None
    currency: str | None = None
    feature_class: str | None = None
    feature_code: str | None = None
    alternate_names: list[str] = []
    mobility_available: bool = False
    modeling_available: bool = True


class GlobalCitySearchResult(BaseModel):
    id: str
    name: str
    country: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    population: int | None = None
    place_type: str = "city"
    mobility_available: bool = False
    modeling_available: bool = True


class GlobalCitySearchResponse(BaseModel):
    results: list[GlobalCitySearchResult]


class CityCoordinates(BaseModel):
    latitude: float | None = None
    longitude: float | None = None


class CityGeographicClassification(BaseModel):
    feature_class: str | None = None
    feature_code: str | None = None
    place_type: str = "city"


class CityProfileCapabilities(BaseModel):
    geographic: bool = True
    context: bool = True
    observed_mobility: bool = False
    cross_city_model: bool = True


class CityProfileResponse(BaseModel):
    city_id: str
    city: str
    country: str | None = None
    country_code: str | None = None
    coordinates: CityCoordinates
    timezone: str | None = None
    currency: str | None = None
    population: int | None = None
    administrative_hierarchy: list[dict[str, str | int | None]] = []
    alternate_names: list[str] = []
    geographic_classification: CityGeographicClassification
    capabilities: CityProfileCapabilities


class ContextSourceEnvelope(BaseModel):
    status: str  # "available" | "unavailable"
    data: dict | list | str | float | int | None = None
    source: str
    timestamp: str
    freshness: str | None = None
    coverage: str | None = None
    reason: str | None = None


class CityContextResponse(BaseModel):
    city_id: str
    city_name: str
    generated_at: str
    context: dict[str, ContextSourceEnvelope]
