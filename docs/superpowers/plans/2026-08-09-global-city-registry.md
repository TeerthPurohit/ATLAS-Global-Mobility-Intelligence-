# Global City Registry & Model Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every city the platform can talk about — NYC, London, and the 522 WorldMove cities — a stable `city_id`, a `model_status` tier (`OBSERVED` / `TRANSFER` / `INSUFFICIENT_DATA`), and a confidence score, sourced from real registered data instead of an ad hoc `population > 0` boolean.

**Architecture:** A new `global_cities` DuckDB table (built by an offline script, same pattern as `city_tariff_profiles`) unions the 2 registered cities (`cities` table, tier `OBSERVED`) with the 522 WorldMove cities (`worldmove_city_population`, tier `TRANSFER`). A new `backend/registry/global_cities.py` module loads it once at startup, mirroring `backend/registry/cities.py`. `global_geography_service.py` consults this registry first (exact `country_code`+name match) before falling back to its existing live-GeoNames population heuristic for the long tail of cities outside the 524.

**Tech Stack:** Python, DuckDB, FastAPI/Pydantic (existing stack — no new dependency).

## Global Constraints

- Never fabricate a `model_status` — a city only gets `OBSERVED` if it has a real `model_registry` row (checked via existing `backend.registry.models`), never based on population alone.
- `city_id` for the 2 existing registered cities stays exactly `"nyc"` / `"london"` (do not rename — dozens of routers/tests/registries key off these strings). Only the 522 new WorldMove-sourced rows get the `{COUNTRY_CODE}_{CITY_NAME}` format (e.g. `IN_JAIPUR`), since they have no existing key to preserve.
- This is a subset of a much larger 55-section spec the user provided (city embeddings, road network, quantile ETA, LLM reasoner, etc.) — this plan implements *only* sections 3 ("global city registry") and a 2-signal subset of section 28 ("confidence score"). Do not implement embeddings, road graphs, or the LLM layer here; those need their own plans.
- Confidence here is a deliberately simple 2-component heuristic (data-tier + feature-completeness), not the full 5-signal formula from the spec (model similarity / prediction stability need city embeddings and multiple trained models this repo doesn't have yet — flag as a `ponytail:` comment, don't build the full formula speculatively).

---

### Task 1: `global_cities` table + build script

**Files:**
- Create: `scripts/build_global_cities.py`
- Test: `tests/test_global_cities_table.py`

**Interfaces:**
- Produces: DuckDB table `global_cities` in `data/warehouse/nyc_rides.duckdb` with columns `city_id VARCHAR PRIMARY KEY, name VARCHAR, country_code VARCHAR, latitude DOUBLE, longitude DOUBLE, timezone VARCHAR, currency VARCHAR, population DOUBLE, population_source VARCHAR, model_status VARCHAR, worldmove_available BOOLEAN`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_global_cities_table.py
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DB_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"


def _table_exists(con) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'global_cities'"
    ).fetchone()[0] > 0


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


def test_global_cities_table_exists_and_populated(con):
    assert _table_exists(con), "run scripts/build_global_cities.py first"
    n = con.execute("SELECT count(*) FROM global_cities").fetchone()[0]
    assert n == 524, f"expected 2 registered + 522 WorldMove cities, got {n}"


def test_global_cities_no_duplicate_ids(con):
    dupes = con.execute(
        "SELECT city_id, count(*) c FROM global_cities GROUP BY 1 HAVING count(*) > 1"
    ).fetchall()
    assert dupes == []


def test_registered_cities_are_observed(con):
    rows = con.execute(
        "SELECT city_id, model_status, population_source FROM global_cities WHERE city_id IN ('nyc', 'london')"
    ).fetchall()
    assert len(rows) == 2
    for city_id, model_status, population_source in rows:
        assert model_status == "OBSERVED", city_id
        assert population_source == "registered", city_id


def test_worldmove_cities_are_transfer(con):
    row = con.execute(
        "SELECT model_status, population_source, worldmove_available FROM global_cities WHERE city_id = 'IN_JAIPUR'"
    ).fetchone()
    assert row is not None, "Jaipur should be present from worldmove_city_population"
    model_status, population_source, worldmove_available = row
    assert model_status == "TRANSFER"
    assert population_source == "worldmove_estimate"
    assert worldmove_available is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_global_cities_table.py -v`
Expected: FAIL — table `global_cities` doesn't exist yet (`_table_exists` is False, first assert fails).

- [ ] **Step 3: Write the build script**

```python
# scripts/build_global_cities.py
"""Build global_cities: the stable, honest registry of every city this
platform can talk about, uniting the 2 real registered cities (cities.csv
-- OBSERVED, they have trained models) with the 522 WorldMove cities
(worldmove_city_population -- TRANSFER, population/mobility prior only,
no trip-level data). See docs/superpowers/plans/2026-08-09-global-city-registry.md.

Existing city_ids ("nyc", "london") are preserved exactly; WorldMove rows
get a new stable {COUNTRY_CODE}_{CITY_NAME} key since they have no prior key
to preserve (checked for collisions -- none exist as of the 522-city load).
"""
import os
import re
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"))


def _slug(country_code: str, city_name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "_", city_name.strip()).strip("_").upper()
    return f"{country_code.upper()}_{name}"


def main():
    con = duckdb.connect(DUCKDB_PATH)

    con.execute("""
        CREATE OR REPLACE TABLE global_cities (
            city_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            country_code VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            timezone VARCHAR,
            currency VARCHAR,
            population DOUBLE,
            population_source VARCHAR,
            model_status VARCHAR,
            worldmove_available BOOLEAN
        )
    """)

    registered = con.execute(
        "SELECT id, name, country_code, latitude, longitude, timezone, currency, population FROM cities"
    ).fetchall()
    rows = [
        (city_id, name, country_code, lat, lon, tz, currency, float(population) if population else None,
         "registered", "OBSERVED", False)
        for city_id, name, country_code, lat, lon, tz, currency, population in registered
    ]

    worldmove = con.execute(
        "SELECT country_code, city_name, population_total FROM worldmove_city_population"
    ).fetchall()
    seen_ids = {r[0] for r in rows}
    for country_code, city_name, population_total in worldmove:
        city_id = _slug(country_code, city_name)
        if city_id in seen_ids:
            raise ValueError(f"city_id collision: {city_id} ({city_name}, {country_code})")
        seen_ids.add(city_id)
        rows.append((
            city_id, city_name, country_code, None, None, None, None,
            population_total, "worldmove_estimate", "TRANSFER", True,
        ))

    con.executemany(
        "INSERT INTO global_cities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    n = con.execute("SELECT count(*) FROM global_cities").fetchone()[0]
    print(f"global_cities: {n:,} rows loaded")
    con.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the script**

Run: `python scripts/build_global_cities.py`
Expected output: `global_cities: 524 rows loaded`

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_global_cities_table.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/build_global_cities.py tests/test_global_cities_table.py
git commit -m "feat: build global_cities registry uniting registered + WorldMove cities"
```

---

### Task 2: `backend/registry/global_cities.py` registry module

**Files:**
- Create: `backend/registry/global_cities.py`
- Test: `tests/test_global_cities_registry.py`

**Interfaces:**
- Consumes: `global_cities` table from Task 1.
- Produces:
  - `load() -> None`
  - `get_city(city_id: str) -> dict | None` — dict has keys `city_id, name, country_code, latitude, longitude, timezone, currency, population, population_source, model_status, worldmove_available`
  - `find_by_name(city_name: str, country_code: str) -> dict | None` — case-insensitive lookup by `(country_code, name)`, used by `global_geography_service` in Task 3 to match a live GeoNames/search result against this registry.
  - `list_cities(model_status: str | None = None) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_global_cities_registry.py
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.registry import global_cities  # noqa: E402


def test_get_city_registered():
    global_cities.load()
    nyc = global_cities.get_city("nyc")
    assert nyc is not None
    assert nyc["model_status"] == "OBSERVED"
    assert nyc["population_source"] == "registered"


def test_get_city_worldmove():
    global_cities.load()
    jaipur = global_cities.get_city("IN_JAIPUR")
    assert jaipur is not None
    assert jaipur["model_status"] == "TRANSFER"
    assert jaipur["worldmove_available"] is True


def test_get_city_unknown_returns_none():
    global_cities.load()
    assert global_cities.get_city("nonexistent_xyz") is None


def test_find_by_name_case_insensitive():
    global_cities.load()
    found = global_cities.find_by_name("jaipur", "IN")
    assert found is not None
    assert found["city_id"] == "IN_JAIPUR"
    assert global_cities.find_by_name("Nonexistentville", "ZZ") is None


def test_list_cities_filters_by_tier():
    global_cities.load()
    observed = global_cities.list_cities(model_status="OBSERVED")
    assert len(observed) == 2
    assert {c["city_id"] for c in observed} == {"nyc", "london"}

    transfer = global_cities.list_cities(model_status="TRANSFER")
    assert len(transfer) == 522
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_global_cities_registry.py -v`
Expected: FAIL — `backend.registry.global_cities` doesn't exist (ImportError).

- [ ] **Step 3: Write the registry module**

```python
# backend/registry/global_cities.py
"""Registry for global_cities (docs/superpowers/plans/2026-08-09-global-city-registry.md)
-- the stable city_id -> tier/population lookup backing global_geography_service's
model_status and confidence fields. Same load-once-at-startup pattern as
backend/registry/cities.py (rule 8: no query-time table scans)."""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

_COLUMNS = (
    "city_id", "name", "country_code", "latitude", "longitude", "timezone",
    "currency", "population", "population_source", "model_status", "worldmove_available",
)

_cities: dict[str, dict] = {}
_by_name: dict[tuple[str, str], dict] = {}


def load() -> None:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        rows = con.execute(f"SELECT {', '.join(_COLUMNS)} FROM global_cities").fetchall()
    finally:
        con.close()
    _cities.clear()
    _by_name.clear()
    for row in rows:
        city = dict(zip(_COLUMNS, row))
        _cities[city["city_id"]] = city
        if city["name"] and city["country_code"]:
            _by_name[(city["country_code"].upper(), city["name"].lower())] = city


def get_city(city_id: str) -> dict | None:
    if not _cities:
        load()  # defensive lazy-load, same rationale as backend/registry/cities.py
    return _cities.get(city_id)


def find_by_name(city_name: str, country_code: str) -> dict | None:
    if not _cities:
        load()
    if not city_name or not country_code:
        return None
    return _by_name.get((country_code.upper(), city_name.lower()))


def list_cities(model_status: str | None = None) -> list[dict]:
    if not _cities:
        load()
    rows = _cities.values()
    if model_status:
        rows = [c for c in rows if c["model_status"] == model_status]
    return list(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_global_cities_registry.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/registry/global_cities.py tests/test_global_cities_registry.py
git commit -m "feat: add global_cities registry module"
```

---

### Task 3: Wire model_status + confidence into `global_geography_service`

**Files:**
- Modify: `backend/services/global_geography_service.py`
- Test: extend `tests/test_global_geography.py`

**Interfaces:**
- Consumes: `backend.registry.global_cities.find_by_name`, `get_city` (Task 2).
- Produces: `resolve_city_tier(city_name, country_code, population, lat) -> tuple[str, float]` returning `(model_status, confidence)` where `model_status in {"OBSERVED", "TRANSFER", "PRIOR_ONLY", "INSUFFICIENT_DATA"}` and `confidence` is a `float` in `[0, 1]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_global_geography.py`:

```python
def test_city_profile_worldmove_city_is_transfer_tier():
    prof = global_geography_service.get_city_profile("jaipur")
    assert prof is not None
    assert prof["model_status"] == "TRANSFER"
    assert 0.0 < prof["confidence"] < 1.0


def test_city_profile_registered_city_is_observed_tier():
    prof = global_geography_service.get_city_profile("nyc")
    assert prof["model_status"] == "OBSERVED"
    assert prof["confidence"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_global_geography.py -k model_status -v`
Expected: FAIL — `get_city_profile` result has no `"model_status"` key yet (`KeyError`).

- [ ] **Step 3: Add `resolve_city_tier` and wire it in**

In `backend/services/global_geography_service.py`, add the import and function (near `resolve_modeling_availability`):

```python
from backend.registry import global_cities as global_cities_registry  # noqa: E402
```

```python
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
```

Then in `get_city_profile()`, after `population`/`population_source` are resolved (the block added earlier in this session), add:

```python
    model_status, confidence = resolve_city_tier(leaf.get("name"), country_code, population, lat)
```

and add both to the returned dict (alongside `"population_source": population_source,`):

```python
        "model_status": model_status,
        "confidence": confidence,
```

For the registered-city branch earlier in the same function (the `if registered:` block near the top), add:

```python
        "model_status": "OBSERVED",
        "confidence": 1.0,
```

to that returned dict too.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_global_geography.py -v`
Expected: PASS (all tests, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add backend/services/global_geography_service.py tests/test_global_geography.py
git commit -m "feat: resolve model_status and confidence from the global_cities registry"
```

---

### Task 4: Expose `model_status`/`confidence` on the API + load registry at startup

**Files:**
- Modify: `backend/schemas_geography.py`
- Modify: `backend/main.py`
- Test: extend `tests/test_global_geography.py`

**Interfaces:**
- Consumes: `model_status`/`confidence` keys on the `get_city_profile()` dict from Task 3.
- Produces: `CityProfileResponse.model_status: str`, `CityProfileResponse.confidence: float`, both required (never fabricated — always set by Task 3).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_global_geography.py`:

```python
def test_city_profile_api_exposes_model_status(client):
    resp = client.get("/api/geography/jaipur")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_status"] == "TRANSFER"
    assert 0.0 < body["confidence"] < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_global_geography.py -k model_status -v`
Expected: FAIL — `Pydantic` validation error, `CityProfileResponse` has no `model_status` field, or the response dict just doesn't include it (`KeyError` in the test's `body["model_status"]`).

- [ ] **Step 3: Add the fields to the schema**

In `backend/schemas_geography.py`, `CityProfileResponse`:

```python
class CityProfileResponse(BaseModel):
    city_id: str
    city: str
    country: str | None = None
    country_code: str | None = None
    coordinates: CityCoordinates
    timezone: str | None = None
    currency: str | None = None
    population: int | None = None
    population_source: str | None = None
    model_status: str
    confidence: float
    administrative_hierarchy: list[dict[str, str | int | None]] = []
    alternate_names: list[str] = []
    geographic_classification: CityGeographicClassification
    capabilities: CityProfileCapabilities
```

- [ ] **Step 4: Wire the registry into app startup**

In `backend/main.py`, alongside the existing `cities_registry.load()` line:

```python
from backend.registry import global_cities as global_cities_registry  # noqa: E402
```

```python
    cities_registry.load()
    global_cities_registry.load()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_global_geography.py -v`
Expected: PASS (full file, including the new API test)

- [ ] **Step 6: Run the full existing test suite to check nothing else broke**

Run: `pytest tests/ -v`
Expected: PASS — no regressions in `test_geography_generalized.py` or any router test that constructs a `CityProfileResponse`.

- [ ] **Step 7: Commit**

```bash
git add backend/schemas_geography.py backend/main.py tests/test_global_geography.py
git commit -m "feat: expose model_status/confidence on the city profile API"
```

---

## Self-Review

**Spec coverage:** Implements spec section 3 (`global_cities`, stable non-name-based keys), section 29 (`OBSERVED`/`TRANSFER`/`PRIOR_ONLY`/`INSUFFICIENT_DATA` tiers), and a deliberately reduced section 28 (confidence — 2 signals, not 5). Section 44 ("modelable city definition") is partially covered: a city from the 524-registry is modelable once it has coordinates + population + a tier; full modelable-ness (weather, road network, tariff) is out of scope here, tracked as follow-up plans.

**Out of scope (needs its own plan):** city embeddings (section 6), road network/routing (sections 13-14), demand/congestion/ETA/surge models (sections 8-10, 15-16), the LLM reasoning layer (sections 11-23 of the LLM-extension doc), quantile predictions (section 27), model registry expansion (section 36), the `/predict/trip` API (section 37), caching (section 48), retraining pipeline (section 26).

**Placeholder scan:** No TBD/TODO; every step has runnable code.

**Type consistency:** `resolve_city_tier` returns `tuple[str, float]` in Task 3 and both values are unpacked and used identically in Task 4's schema (`model_status: str`, `confidence: float`). `global_cities.get_city`/`find_by_name` return `dict | None` consistently across Tasks 2 and 3.
