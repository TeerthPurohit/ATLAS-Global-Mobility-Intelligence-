"""Loads precomputed platform-introspection artifacts once at startup (rule 8):
model metrics, algorithm benchmarks, dbt run status. Backs the platform-health
and provenance widgets that used to be hardcoded in the frontend (see
ARCHITECTURE_AUDIT.md). Only /warehouse/* and /health run a query per request
-- both are cheap point lookups, not table scans.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
DBT_TARGET = REPO_ROOT / "dbt_project" / "target"

MODEL_METADATA_PATHS = {
    "linear": REPO_ROOT / "models" / "linear_baseline" / "linear_model_metadata.json",
    "ewma": REPO_ROOT / "models" / "ewma_baseline" / "ewma_baseline_metadata.json",
    "xgboost": REPO_ROOT / "models" / "xgboost_model" / "xgb_metadata.json",
    "lstm": REPO_ROOT / "models" / "lstm_model" / "lstm_metadata.json",
}
COMPARE_RESULTS_PATH = REPO_ROOT / "models" / "evaluation" / "compare_results.json"
FARE_METADATA_PATH = REPO_ROOT / "models" / "fare_prediction" / "fare_xgb_metadata.json"
KDTREE_BENCHMARK_PATH = REPO_ROOT / "algorithms" / "spatial" / "output" / "kdtree_benchmark.json"
PAGERANK_HUBS_PATH = REPO_ROOT / "algorithms" / "graph" / "output" / "pagerank_hubs.json"

WAREHOUSE_TABLES = (
    "stg_trips",
    "stg_zones",
    "int_trips_enriched",
    "zone_hourly_demand",
    "zone_fare_stats",
    "zone_pair_flows",
)

_artifacts: dict = {}


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load() -> None:
    """Read every artifact file once. Call from FastAPI's startup hook."""
    _artifacts["compare_results"] = _read_json(COMPARE_RESULTS_PATH)
    _artifacts["model_metadata"] = {name: _read_json(path) for name, path in MODEL_METADATA_PATHS.items()}
    _artifacts["fare_metadata"] = _read_json(FARE_METADATA_PATH)
    _artifacts["kdtree_benchmark"] = _read_json(KDTREE_BENCHMARK_PATH)
    _artifacts["pagerank_hubs"] = _read_json(PAGERANK_HUBS_PATH)
    _artifacts["dbt_run_results"] = _read_json(DBT_TARGET / "run_results.json")
    _artifacts["dbt_manifest"] = _read_json(DBT_TARGET / "manifest.json")


def get_demand_model_metrics() -> dict:
    compare = _artifacts.get("compare_results") or {}
    metadata = _artifacts.get("model_metadata") or {}
    result = {}
    for name, metrics in compare.items():
        meta = metadata.get(name) or {}
        result[name] = {
            **metrics,
            "hyperparameters": meta.get("hyperparameters"),
            "feature_importances": meta.get("feature_importances"),
        }
    return result


def get_fare_model_metrics() -> dict | None:
    return _artifacts.get("fare_metadata")


def get_algorithm_benchmarks() -> dict:
    return {
        "kdtree": _artifacts.get("kdtree_benchmark"),
        "pagerank": _artifacts.get("pagerank_hubs"),
    }


def get_pipeline_status() -> dict:
    run_results = _artifacts.get("dbt_run_results")
    if run_results is None:
        return {"available": False, "stages": []}
    stages = [
        {
            "unique_id": r["unique_id"],
            "status": r["status"],
            "execution_time_seconds": r["execution_time"],
            "rows_affected": (r.get("adapter_response") or {}).get("rows_affected"),
        }
        for r in run_results.get("results", [])
    ]
    return {
        "available": True,
        "generated_at": run_results.get("metadata", {}).get("generated_at"),
        "dbt_version": run_results.get("metadata", {}).get("dbt_version"),
        "elapsed_time_seconds": run_results.get("elapsed_time"),
        "stages": stages,
    }


def get_dashboard_summary() -> dict:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        total_trips, weighted_avg_fare, n_zones = con.execute(
            """
            select
                sum(total_trips),
                sum(avg_fare * total_trips) / nullif(sum(total_trips), 0),
                count(distinct pickup_location_id)
            from zone_hourly_demand
            """
        ).fetchone()
    finally:
        con.close()
    return {
        "total_trips": int(total_trips or 0),
        "avg_fare": float(weighted_avg_fare or 0.0),
        "active_zones": int(n_zones or 0),
    }


def get_hourly_demand_profile() -> list[dict]:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        rows = con.execute(
            """
            select
                pickup_hour,
                sum(total_trips) as demand,
                sum(avg_fare * total_trips) / nullif(sum(total_trips), 0) as fare
            from zone_hourly_demand
            group by 1
            order by 1
            """
        ).fetchall()
    finally:
        con.close()
    return [{"hour": int(h), "demand": int(d), "fare": round(float(f), 2)} for h, d, f in rows]


def get_warehouse_stats() -> dict:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        row_counts = {
            table: con.execute(f'select count(*) from "{table}"').fetchone()[0] for table in WAREHOUSE_TABLES
        }
    finally:
        con.close()
    return {
        "row_counts": row_counts,
        "total_rows": sum(row_counts.values()),
        "warehouse_file_bytes": WAREHOUSE_PATH.stat().st_size,
        "warehouse_last_modified": WAREHOUSE_PATH.stat().st_mtime,
    }


def get_warehouse_tables() -> list[dict]:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        tables = []
        for table in WAREHOUSE_TABLES:
            columns = con.execute(f'describe "{table}"').fetchdf().to_dict(orient="records")
            row_count = con.execute(f'select count(*) from "{table}"').fetchone()[0]
            tables.append({"table": table, "row_count": row_count, "columns": columns})
    finally:
        con.close()
    return tables


def get_insight_docs(limit: int = 20) -> list[dict]:
    """Real per-zone insight paragraphs from rag/insight_generation (FR-1) --
    not computed here, just read and sorted busiest-first for the frontend."""
    sys.path.insert(0, str(REPO_ROOT / "rag" / "insight_generation"))
    from generate_insight_docs import load_insight_docs  # noqa: PLC0415

    docs = load_insight_docs()
    docs.sort(key=lambda d: d.get("total_trips") or 0, reverse=True)
    return docs[:limit]


def check_health() -> dict:
    duckdb_ok = False
    try:
        con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
        con.execute("select 1").fetchone()
        con.close()
        duckdb_ok = True
    except Exception:
        duckdb_ok = False

    qdrant_ok = False
    try:
        rag_dir = REPO_ROOT / "rag"
        if str(rag_dir) not in sys.path:
            sys.path.insert(0, str(rag_dir))
        from config import QDRANT_URL  # noqa: PLC0415
        from qdrant_client import QdrantClient  # noqa: PLC0415

        client = QdrantClient(url=QDRANT_URL, timeout=2)
        client.get_collections()
        qdrant_ok = True
    except Exception:
        qdrant_ok = False

    return {
        "duckdb": "online" if duckdb_ok else "unavailable",
        "qdrant": "online" if qdrant_ok else "unavailable",
        "status": "healthy" if duckdb_ok else "degraded",
    }
