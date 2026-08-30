"""FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup
(rule 8) before accepting traffic."""

from __future__ import annotations

import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()  # API keys must be set before adapters read os.environ at import time

RAG_DIR = Path(__file__).resolve().parent.parent / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import llm_usage  # noqa: E402

# Structured logging (SPEC-013 FR-14 + logging rule: every API logs the steps
# it goes through and which step it fails). loguru's default sink already
# gives readable per-call-site formatting; this just fixes the level and
# format so every router's `from loguru import logger` calls are consistent.
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} {level} {name}: {message}")

from fastapi import Depends, FastAPI  # noqa: E402, I001
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402

from backend.errors import DomainError  # noqa: E402
from backend.registry import cities as cities_registry  # noqa: E402
from backend.registry import models as models_registry  # noqa: E402
from backend.registry import transit as transit_registry  # noqa: E402
from backend.routers import auth, chat, city, context, journey, model_predictions, platform, predictions, zones, mobility, analytics, docs_api  # noqa: E402
from backend.services import auth_service, journey_service, model_service, platform_service, tariff_profiles  # noqa: E402


# One missing artifact used to take down the whole API: these ran unguarded, so a
# failure in any one of them aborted the lifespan and nothing served. Each is now
# isolated -- a loader that fails disables its own features (the registries and
# services already report "unavailable" when their state is empty) instead of the app.
_STARTUP_LOADERS = (
    ("model_service", model_service.load),
    ("tariff_profiles", tariff_profiles.load),
    ("platform_service", platform_service.load),
    ("journey_service", journey_service.load),
    ("models_registry", models_registry.load),
    ("transit_registry", transit_registry.load),
    ("cities_registry", cities_registry.load),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    failed = []
    for name, load in _STARTUP_LOADERS:
        logger.info("Loading {}...", name)
        try:
            load()
        except Exception:  # noqa: BLE001
            failed.append(name)
            logger.exception("{} failed to load - its features will report unavailable", name)
    if failed:
        logger.warning("Started with {}/{} loaders failed: {}", len(failed), len(_STARTUP_LOADERS), ", ".join(failed))
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


@app.middleware("http")
async def log_requests(request, call_next):
    """Every API request/response/failure logs through here (logging rule:
    log the steps an API goes through and which step it fails). Per-endpoint
    step logs (logger.info inside routers) fill in what happened between this
    request-start and request-end line, so an error here plus the last step
    line logged inside the handler pinpoints exactly which step failed."""
    start = time.monotonic()
    llm_usage.reset()
    logger.info("-> {} {}", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.exception("<- {} {} failed after {:.1f}ms", request.method, request.url.path, elapsed_ms)
        raise
    elapsed_ms = (time.monotonic() - start) * 1000
    usage = llm_usage.summary()
    if usage["llm_calls"]:
        logger.info(
            "<- {} {} {} ({:.1f}ms, llm_calls={} tokens={} cost_usd={})",
            request.method, request.url.path, response.status_code, elapsed_ms,
            usage["llm_calls"], usage["total_tokens"], usage["cost_usd"],
        )
    else:
        logger.info("<- {} {} {} ({:.1f}ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


# auth.router (signup/login/logout/me) and platform.router (just /health)
# are the only endpoints reachable without a session -- everything else is
# real ride/demand/fare data and must not be callable by an unauthenticated
# client, so every other router is gated behind the same session-cookie
# dependency `GET /auth/me` already uses.
_REQUIRE_SESSION = [Depends(auth_service.get_current_user)]

app.include_router(auth.router)
app.include_router(platform.router)
app.include_router(docs_api.router)
app.include_router(predictions.router, dependencies=_REQUIRE_SESSION)
app.include_router(model_predictions.router, dependencies=_REQUIRE_SESSION)
app.include_router(zones.router, dependencies=_REQUIRE_SESSION)
app.include_router(chat.router, dependencies=_REQUIRE_SESSION)
app.include_router(platform.router_protected, dependencies=_REQUIRE_SESSION)
app.include_router(journey.router, dependencies=_REQUIRE_SESSION)
app.include_router(city.router, dependencies=_REQUIRE_SESSION)
app.include_router(mobility.router, dependencies=_REQUIRE_SESSION)
app.include_router(context.router, dependencies=_REQUIRE_SESSION)
app.include_router(analytics.router, dependencies=_REQUIRE_SESSION)


# Alternate API-playground UIs alongside FastAPI's default /docs (Swagger) and
# /redoc -- all three read the same live schema at /openapi.json, no separate
# spec to keep in sync. CDN-hosted web components, no new backend dependency.
@app.get("/scalar", include_in_schema=False, response_class=HTMLResponse)
def scalar_docs() -> str:
    logger.info("GET /scalar step=start")
    return """<!doctype html>
<html><head><title>API Reference (Scalar)</title></head>
<body>
<script id="api-reference" data-url="/openapi.json"></script>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
</body></html>"""


@app.get("/rapidoc", include_in_schema=False, response_class=HTMLResponse)
def rapidoc_docs() -> str:
    logger.info("GET /rapidoc step=start")
    return """<!doctype html>
<html><head><title>API Reference (RapiDoc)</title>
<script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
</head>
<body>
<rapi-doc spec-url="/openapi.json" theme="dark" render-style="focused" show-header="false" allow-authentication="true" persist-auth="true"></rapi-doc>
</body></html>"""


@app.get("/explorer", include_in_schema=False, response_class=HTMLResponse)
def openapi_explorer_docs() -> str:
    logger.info("GET /explorer step=start")
    return """<!doctype html>
<html><head><title>API Reference (OpenAPI Explorer)</title>
<script type="module" src="https://unpkg.com/openapi-explorer/dist/browser/openapi-explorer.min.js"></script>
</head>
<body>
<openapi-explorer spec-url="/openapi.json"></openapi-explorer>
</body></html>"""


@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code.value, "message": exc.message}})
