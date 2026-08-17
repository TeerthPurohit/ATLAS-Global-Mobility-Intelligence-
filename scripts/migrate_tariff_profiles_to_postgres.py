"""One-time copy of `city_tariff_profiles` from the local DuckDB warehouse
into the RDS Postgres instance (see backend/services/tariff_profiles.py's
module docstring for why: a recurring Claude Code cloud routine that
re-validates stale/new-city tariff profiles runs in an isolated sandbox with
only a git checkout, so it can never reach the local DuckDB file).

Run once, by hand:
    python scripts/migrate_tariff_profiles_to_postgres.py

Idempotent: reuses `tariff_profiles.upsert()`, which DELETEs then INSERTs by
city_id, so re-running this after a partial failure just re-copies every row
again rather than erroring on a duplicate key.

After this runs, DuckDB's copy of this one table is a frozen, stale mirror
-- see the module docstring in tariff_profiles.py. Nothing else in this
repo's DuckDB warehouse is affected.
"""
from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

import duckdb
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from backend.services.tariff_profiles import (  # noqa: E402
    TABLE_NAME,
    WAREHOUSE_PATH,
    TariffProfile,
    city_ids,
    load,
    upsert,
)

_FIELD_NAMES = [f.name for f in fields(TariffProfile)]


def _read_duckdb_rows() -> list[dict]:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        existing = {r[0] for r in con.execute(f"DESCRIBE {TABLE_NAME}").fetchall()}
        columns = [c for c in _FIELD_NAMES if c in existing]
        rows = con.execute(f"SELECT {', '.join(columns)} FROM {TABLE_NAME} ORDER BY city_id").fetchall()
    finally:
        con.close()
    out = []
    for row in rows:
        data = dict(zip(columns, row))
        if data.get("generated_at") is not None:
            data["generated_at"] = str(data["generated_at"])
        for name in ("effective_from", "extras_backfilled_at", "validated_at"):
            if data.get(name) is not None:
                data[name] = str(data[name]) if not isinstance(data[name], str) else data[name]
        out.append(data)
    return out


def migrate() -> int:
    rows = _read_duckdb_rows()
    print(f"migrate_tariff_profiles_to_postgres: {len(rows)} rows read from DuckDB {WAREHOUSE_PATH}")
    for data in rows:
        upsert(TariffProfile(**data))
    print(f"migrate_tariff_profiles_to_postgres: {len(rows)} rows upserted into Postgres")
    return len(rows)


def demo() -> None:
    """Self-check: migrate, then confirm Postgres has every DuckDB city_id
    and IN_MUMBAI's real evidence-validated numbers came through intact."""
    n = migrate()
    load()  # force a fresh read from Postgres, bypassing the module cache
    pg_ids = set(city_ids())
    duck_ids = {r["city_id"] for r in _read_duckdb_rows()}
    assert duck_ids <= pg_ids, f"missing in Postgres: {duck_ids - pg_ids}"

    from backend.services.tariff_profiles import get

    mumbai = get("IN_MUMBAI")
    assert mumbai is not None
    assert mumbai.base_fare == 31.0 and mumbai.per_km == 28.0
    assert mumbai.validation_method == "web_search_corroborated"
    assert mumbai.evidence_sources is not None
    print(f"migrate_tariff_profiles_to_postgres demo OK: {n} rows, IN_MUMBAI validated ({mumbai.base_fare}/{mumbai.per_km})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        migrate()
