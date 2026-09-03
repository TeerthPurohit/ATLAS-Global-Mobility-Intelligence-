FROM python:3.12-slim

WORKDIR /app

# System dependencies (curl for the HEALTHCHECK below; xgboost/duckdb ship
# prebuilt wheels so no build-essential needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch: the serving path only ever runs inference on CPU
# (model_service.py loads with map_location="cpu"), but the default PyPI
# wheel bundles CUDA/cuDNN/cuBLAS/NCCL (~1-2GB of unused GPU runtime libs).
# Installing from PyTorch's CPU-only index first means the requirements
# install below finds torch's version constraint already satisfied and
# never reaches for the CUDA wheel.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Runtime-only deps -- NOT requirements.txt, which also carries dbt/notebook
# deps (dbt-core, scipy, networkx, jupyter, matplotlib, pytest) that don't
# belong in the deployed API image. torch and scikit-learn ARE here: both are
# real serving deps (see the comments in requirements-backend.txt).
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

RUN useradd -m appuser

# Copy application code (data/models/backend/rag are bind-mounted by docker-compose.yml at runtime)
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser rag ./rag
COPY --chown=appuser:appuser algorithms ./algorithms
# data/ is copied file-by-file rather than wholesale: `COPY data ./data` used to
# pull the entire 12GB local warehouse into the image. Per ADR-005 the deployed
# backend gets only the slim precomputed artifact from
# scripts/build_deployed_duckdb.py, landed at the canonical warehouse path so
# the services' WAREHOUSE_PATH resolves unchanged.
COPY --chown=appuser:appuser data/lookup ./data/lookup
COPY --chown=appuser:appuser data/ingestion_report.md data/tariff_calibration.json ./data/
COPY --chown=appuser:appuser data/warehouse/deployed.duckdb ./data/warehouse/nyc_rides.duckdb
COPY --chown=appuser:appuser models ./models
# Only target/ (dbt manifest/run_results json, read by platform_service.py
# for /pipeline/status) and seeds/ (vehicle_profiles.csv, read by
# backend/services/vehicle_profiles.py; fixed_holidays_extended.csv, read by
# backend/adapters/holidays_nager.py) are ever read at runtime -- confirmed
# by grepping every dbt_project reference under backend/ and rag/. The rest
# of dbt_project (models/, macros/, dbt_packages/, compiled SQL) is never
# touched by the running API.
COPY --chown=appuser:appuser dbt_project/target ./dbt_project/target
COPY --chown=appuser:appuser dbt_project/seeds ./dbt_project/seeds

USER appuser

EXPOSE 8000

# /health always returns HTTP 200, even when DuckDB/Qdrant are down --
# platform_service.check_health() reports degraded state in the JSON body,
# not the status code -- so this greps the body instead of trusting curl's
# exit code alone.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" | grep -q '"status":"healthy"' || exit 1

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
