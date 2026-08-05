"""Shared config for the RAG layer -- one place for the LLM model id and
warehouse path so they aren't duplicated across generate_insight_docs.py,
sql_agent.py, query_classifier.py, and rag_pipeline.py.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-nano")
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse" / "nyc_rides.duckdb"
# Qdrant service from docker-compose.yml; localhost default for running
# rag/ scripts outside the backend container during local dev.
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
