#!/usr/bin/env python3
"""Resumable tariff profile generation with retry/backoff and skip-already-done.

Reuses the existing generate_tariff_profile.py logic (which already builds
LLM-anchored profiles) but wraps it to:
- Skip any city_id that already has a valid row in city_tariff_profiles
- Retry with exponential backoff on transient DuckDB lock errors
- Log progress so you can see how many are done vs remaining
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.services.tariff_profiles import TariffProfile, upsert, get, load  # noqa: E402
from scripts.generate_tariff_profile import build_profile  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def already_done(city_id: str) -> bool:
    """Check if city already has a valid profile (handles both in-memory cache and DB)."""
    # Quick check from in-memory cache if loaded
    if get(city_id) is not None:
        return True
    # Check DB directly (fresh read)
    try:
        con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
        try:
            row = con.execute(
                "SELECT 1 FROM city_tariff_profiles WHERE city_id = ? LIMIT 1", [city_id]
            ).fetchone()
            return row is not None
        finally:
            con.close()
    except Exception:
        return False


def generate_with_retry(city_id: str, max_retries: int = 5) -> bool:
    """Generate a single profile with retry/backoff on lock errors."""
    for attempt in range(1, max_retries + 1):
        try:
            profile = build_profile(city_id)
            upsert(profile)
            log.info("[ok] %s: %s base=%.2f per_km=%.2f per_min=%.2f min_fare=%.2f confidence=%.2f",
                     city_id, profile.currency, profile.base_fare, profile.per_km,
                     profile.per_min, profile.min_fare, profile.confidence)
            return True
        except Exception as exc:  # noqa: BLE001
            if "IO Error" in str(exc) and "being used by another process" in str(exc):
                wait = min(2 ** attempt, 30)
                log.warning("DB locked for %s (attempt %d/%d), retrying in %ds...",
                            city_id, attempt, max_retries, wait)
                time.sleep(wait)
                continue
            log.error("[fail] %s: %s", city_id, exc)
            return False
    log.error("[fail] %s: max retries exhausted", city_id)
    return False


def main(city_ids: list[str]) -> None:
    # Warm up the profile cache so we know what's already done
    load()
    done = sum(1 for cid in city_ids if already_done(cid))
    remaining = [cid for cid in city_ids if not already_done(cid)]
    log.info("Total: %d | Already done: %d | Remaining: %d",
             len(city_ids), done, len(remaining))

    success = 0
    failed = 0
    for i, city_id in enumerate(remaining, 1):
        if generate_with_retry(city_id):
            success += 1
        else:
            failed += 1
        if i % 10 == 0:
            log.info("Progress: %d/%d done, %d failed", i + success + failed - i, len(remaining), failed)

    log.info("FINAL: %d success, %d failed, %d already existed",
             success, failed, done)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_tariff_resumable.py <city_id> [<city_id> ...]")
        sys.exit(1)
    main(sys.argv[1:])