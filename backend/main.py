"""FastAPI app (FR-1). Mounts routers; loads model artifacts once at startup
(rule 8) before accepting traffic."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.routers import predictions, zones
from backend.services import model_service

# chat router depends on rag/rag_pipeline.py, which is still a stub.
# Uncomment once backend/routers/chat.py and rag/rag_pipeline.py are built:
# from backend.routers import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_service.load()  # runs once, before the app accepts traffic (rule 8)
    yield


app = FastAPI(title="NYC Ride Intelligence API", lifespan=lifespan)

app.include_router(predictions.router)
app.include_router(zones.router)
# app.include_router(chat.router)
