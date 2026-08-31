FROM python:3.12-slim

WORKDIR /app

# System dependencies (curl for healthcheck; xgboost/duckdb ship prebuilt
# wheels so no build-essential needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Runtime-only deps -- NOT requirements.txt, which also carries
# training/dbt/notebook deps (torch, dbt-core, scikit-learn, scipy,
# jupyter...) that don't belong in the deployed API image.
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

# Copy application code (data/models/backend/rag are bind-mounted by docker-compose.yml at runtime)
COPY backend ./backend
COPY rag ./rag
COPY algorithms ./algorithms
# These directories contain the runtime code and any production artifacts that
# are present in the deployment checkout. The warehouse should be a slim,
# precomputed file; raw TLC data must not be copied into the image.
COPY data ./data
COPY models ./models
COPY dbt_project ./dbt_project

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
