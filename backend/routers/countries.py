"""GET /api/countries, GET /api/countries/{code} (SPEC-013 FR-9). Thin:
delegates to backend/registry/countries.py, raises DomainError for a code
this platform doesn't carry a row for.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.errors import DomainError
from backend.registry import countries as countries_registry
from backend.schemas import CountriesResponse, Country, ErrorCode, ErrorResponse

router = APIRouter(prefix="/api/countries", tags=["Countries"])


@router.get(
    "",
    response_model=CountriesResponse,
    summary="List all countries",
    description="Every country registered in the Global Mobility Domain Model. "
    "`supported` is true iff the country has >=1 onboarded city.",
)
def list_countries() -> CountriesResponse:
    return CountriesResponse(countries=[Country(**c) for c in countries_registry.list_countries()])


@router.get(
    "/{code}",
    response_model=Country,
    summary="Get a country",
    responses={404: {"model": ErrorResponse, "description": "Country not supported"}},
)
def get_country(code: str) -> Country:
    country = countries_registry.get_country(code)
    if country is None:
        raise DomainError(ErrorCode.COUNTRY_NOT_SUPPORTED, f"country not supported: {code!r}", 404)
    return Country(**country)
