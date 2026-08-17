"""Global Geography Registry Service (Phase 1).

Resolves arbitrary global places (cities, administrative divisions, airports,
stations, metros) dynamically from registered seeds, GeoNames, and Google Places,
separating global geography from mobility data availability and modeling capabilities.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import duckdb
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.registry import cities as cities_registry  # noqa: E402
from backend.registry import global_cities as global_cities_registry  # noqa: E402
from backend.services import geonames_service  # noqa: E402

_WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"


@lru_cache(maxsize=1)
def _worldmove_population() -> dict[tuple[str, str], float]:
    """(country_code, city_name.lower()) -> population_total, from the 522-city
    WorldMove grid summaries (scripts/load_worldmove_to_duckdb.py). This is a
    modeled population signal, not a GeoNames-measured figure -- callers must
    keep it labeled as such, never presented as an authoritative population."""
    try:
        con = duckdb.connect(str(_WAREHOUSE_PATH), read_only=True)
        try:
            rows = con.execute(
                "SELECT country_code, city_name, population_total FROM worldmove_city_population"
            ).fetchall()
        finally:
            con.close()
    except duckdb.Error as exc:  # noqa: BLE001 -- table/file missing degrades to no fallback, never a crash
        logger.debug("global_geography_service._worldmove_population step=table_missing reason={}", exc)
        return {}
    return {(cc, name.lower()): pop for cc, name, pop in rows}


def get_worldmove_population(city_name: str | None, country_code: str | None) -> float | None:
    if not city_name or not country_code:
        return None
    return _worldmove_population().get((country_code.upper(), city_name.lower()))

@lru_cache(maxsize=1)
def _country_currencies() -> dict[str, str]:
    """ISO 4217 currency per country, straight from GeoNames'
    `countryInfoJSON` -- covers every country, not a hand-maintained
    shortlist that silently defaults the rest of the world to USD."""
    return {
        c["iso2"]: c["currency"]
        for c in geonames_service.get_all_countries()
        if c.get("iso2") and c.get("currency")
    }


def get_currency_for_country(country_code: str | None) -> str:
    if not country_code:
        return "USD"
    try:
        return _country_currencies().get(country_code.upper(), "USD")
    except Exception as exc:  # noqa: BLE001 -- GeoNames unavailable degrades to USD, never a hard failure
        logger.warning("global_geography_service.get_currency_for_country step=geonames failed country_code={} reason={}", country_code, exc)
        return "USD"


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


def resolve_city_tier(city_name: str | None, country_code: str | None, population: float | None, lat: float | None) -> tuple[str, float]:
    """(model_status, confidence). Checks the 524-city global_cities registry
    first (Task 2) -- exact (country_code, name) match -- before falling back
    to a population-only heuristic for cities outside that registry.

    Confidence is a 2-signal heuristic (data tier + feature completeness),
    not the full 5-signal formula from the spec -- that needs city
    embeddings and multiple trained models this repo doesn't have yet.
    # ponytail: 2-signal confidence, add model-similarity/prediction-stability
    # signals once city embeddings (a separate, larger plan) exist.
    """
    registered = global_cities_registry.find_by_name(city_name, country_code) if city_name and country_code else None
    if registered:
        status = registered["model_status"]
    elif population and population > 0:
        status = "PRIOR_ONLY"
    else:
        status = "INSUFFICIENT_DATA"

    tier_score = {"OBSERVED": 1.0, "TRANSFER": 0.6, "PRIOR_ONLY": 0.3, "INSUFFICIENT_DATA": 0.0}[status]
    completeness = sum([population is not None, lat is not None]) / 2
    confidence = round((tier_score + completeness) / 2, 2) if status != "OBSERVED" else 1.0
    return status, confidence


def get_city_profile(city_id: str) -> dict | None:
    """Phase 3: Fetch authoritative geographic facts for a city_id or geoname_id."""
    logger.debug("global_geography_service.get_city_profile step=start city_id={}", city_id)
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
            "model_status": "OBSERVED",
            "confidence": 1.0,
        }

    # 524-city global registry (WorldMove-backed OBSERVED/TRANSFER/PRIOR_ONLY
    # tiers) -- direct city_id lookup against the real primary key (e.g.
    # "FR_MARSEILLE"), no network call. This was previously unreachable: the
    # only path into the 524-city table was `resolve_city_tier`'s
    # `find_by_name`, called *after* a live GeoNames search had already
    # resolved a name -- so passing the registry's own city_id (what the
    # frontend's city picker actually sends) fell through to GeoNames search
    # by that raw id string ("FR_MARSEILLE" is not a place name GeoNames can
    # find), returning None even for a city this repo has real WorldMove
    # population data for.
    global_city = global_cities_registry.get_city(city_id)
    if global_city:
        model_status, confidence = resolve_city_tier(
            global_city.get("name"), global_city.get("country_code"),
            global_city.get("population"), global_city.get("latitude"),
        )
        currency = global_city.get("currency") or get_currency_for_country(global_city.get("country_code"))
        return {
            "city_id": global_city["city_id"],
            "city": global_city.get("name"),
            "country": global_city.get("country_code"),
            "country_code": global_city.get("country_code"),
            "coordinates": {
                "latitude": global_city.get("latitude"),
                "longitude": global_city.get("longitude"),
            },
            "timezone": global_city.get("timezone") or "UTC",
            "currency": currency,
            "population": global_city.get("population"),
            "population_source": global_city.get("population_source"),
            "model_status": model_status,
            "confidence": confidence,
            "administrative_hierarchy": [
                {"name": global_city.get("name"), "type": "city"},
                {"name": global_city.get("country_code"), "type": "country"},
            ],
            "alternate_names": [global_city["name"]] if global_city.get("name") else [],
            "geographic_classification": {
                "feature_class": "P",
                "feature_code": "PPL",
                "place_type": "city",
            },
            "capabilities": {
                "geographic": True,
                "context": True,
                "observed_mobility": False,
                "cross_city_model": resolve_modeling_availability(global_city.get("population"), global_city.get("latitude")),
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
            logger.debug("global_geography_service.get_city_profile step=hierarchy_lookup failed geoname_id={} reason={}", geoname_id, exc)

    if not raw_hierarchy:
        # Search by place name
        places = geonames_service.search_places(city_id)
        if not places:
            logger.info("global_geography_service.get_city_profile step=unresolvable city_id={}", city_id)
            return None
        place = places[0]
        geoname_id = place.get("geoname_id")
        if geoname_id:
            try:
                raw_hierarchy = geonames_service.get_hierarchy(geoname_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("global_geography_service.get_city_profile step=hierarchy_lookup failed geoname_id={} reason={}", geoname_id, exc)
                raw_hierarchy = []

    if not geoname_id and not places:
        return None

    leaf = raw_hierarchy[-1] if raw_hierarchy else places[0]
    lat = geonames_service._num(leaf.get("latitude")) or geonames_service._num(leaf.get("lat"))
    lng = geonames_service._num(leaf.get("longitude")) or geonames_service._num(leaf.get("lng"))

    country_code = leaf.get("country_code") or leaf.get("countryCode")
    country_name = leaf.get("country_name") or leaf.get("countryName")
    population = leaf.get("population")
    population_source = "geonames" if population else None
    if not population:
        population = get_worldmove_population(leaf.get("name"), country_code)
        if population:
            population = int(round(population))
            population_source = "worldmove_estimate"

    model_status, confidence = resolve_city_tier(leaf.get("name"), country_code, population, lat)

    tz_id = "UTC"
    if lat is not None and lng is not None:
        try:
            tz = geonames_service.get_timezone(lat, lng)
            tz_id = tz.get("timezone_id") or "UTC"
        except Exception as exc:  # noqa: BLE001
            logger.debug("global_geography_service.get_city_profile step=timezone_lookup failed lat={} lng={} reason={}", lat, lng, exc)

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
        "population_source": population_source,
        "model_status": model_status,
        "confidence": confidence,
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
        name = p.get("name") or query_clean.title()
        cc = p.get("country_code")
        cname = p.get("country_name") or cc

        population = p.get("population")
        population_source = "geonames" if population else None
        if not population:
            population = get_worldmove_population(name, cc)
            if population:
                population = int(round(population))
                population_source = "worldmove_estimate"
        if not population:
            continue
        seen_ids.add(gid)

        results.append({
            "id": gid,
            "name": name,
            "country": cname,
            "country_code": cc,
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "timezone": None,
            "population": population,
            "population_source": population_source,
            "place_type": _classify_place_type(p.get("feature_class"), p.get("feature_code")),
            "mobility_available": False,
            "modeling_available": True,
        })
        if len(results) >= limit:
            break

    return results[:limit]
