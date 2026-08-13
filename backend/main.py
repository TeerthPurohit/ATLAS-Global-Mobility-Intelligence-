"""FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup
(rule 8) before accepting traffic."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # OPENWEATHER_API_KEY etc. must be set before adapters read os.environ at import time

# Structured logging (SPEC-013 FR-14, stdlib only, no new infra) -- city
# resolution, model resolution, capability checks, and query-plan
# compilation/execution log through this at INFO.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from backend.errors import DomainError  # noqa: E402
from backend.errors_geography import GeographyError  # noqa: E402
from backend.registry import cities as cities_registry  # noqa: E402
from backend.registry import countries as countries_registry  # noqa: E402
from backend.registry import global_cities as global_cities_registry  # noqa: E402
from backend.registry import models as models_registry  # noqa: E402
from backend.registry import transit as transit_registry  # noqa: E402
from backend.routers import chat, cities, countries, context, geography, journey, platform, predictions, zones, mobility, analytics  # noqa: E402
from backend.services import journey_service, model_service, platform_service, tariff_profiles  # noqa: E402

logger = logging.getLogger("backend.startup")


# One missing artifact used to take down the whole API: these ran unguarded, so a
# failure in any one of them aborted the lifespan and nothing served. Each is now
# isolated -- a loader that fails disables its own features (the registries and
# services already report "unavailable" when their state is empty) instead of the app.
_STARTUP_LOADERS = (
    ("model_service", model_service.load),
    ("tariff_profiles", tariff_profiles.load),
    ("platform_service", platform_service.load),
    ("journey_service", journey_service.load),
    ("countries_registry", countries_registry.load),
    ("models_registry", models_registry.load),
    ("transit_registry", transit_registry.load),
    ("cities_registry", cities_registry.load),
    ("global_cities_registry", global_cities_registry.load),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    failed = []
    for name, load in _STARTUP_LOADERS:
        logger.info("Loading %s...", name)
        try:
            load()
        except Exception:
            failed.append(name)
            logger.exception("%s failed to load - its features will report unavailable", name)
    if failed:
        logger.warning("Started with %d/%d loaders failed: %s",
                       len(failed), len(_STARTUP_LOADERS), ", ".join(failed))
    else:
        logger.info("All services loaded!")
    yield


app = FastAPI(title="NYC Ride Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3004",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://frontend:5173",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(zones.router)
app.include_router(chat.router)
app.include_router(platform.router)
app.include_router(journey.router)
app.include_router(geography.router)
app.include_router(countries.router)
app.include_router(cities.router)
app.include_router(mobility.router)
app.include_router(context.router)
app.include_router(analytics.router)


@app.exception_handler(GeographyError)
async def geography_error_handler(request, exc: GeographyError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code.value, "message": exc.message}})


@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code.value, "message": exc.message}})
