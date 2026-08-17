"""Standing worklist for evidence-grounded tariff validation (2026-08-16).

The one-off fix for the 374 duplicate-templated cities isn't enough on its
own -- new cities get added to the registry over time, and even a correctly
validated profile goes stale. This module is the piece both the initial
backfill AND a recurring scheduled agent call to answer the same question:
"which cities need a validate_tariff_city.py pass right now?"

A city needs validation if ANY of:
  - it has NO tariff profile row at all (new city, never processed)
  - its profile was never evidence-validated (validation_method IS NULL --
    the original 517 llm_anchored rows from 2026-08-09)
  - its profile's evidence-backed numbers are stale (validated_at older than
    STALE_AFTER_DAYS)

NYC and London are excluded -- they have real trained fare models
(model_service.predict_fare), never a tariff profile at all (see
tariff_profiles.py's module docstring).

Usage:
    python scripts/find_cities_needing_tariff_validation.py            # human-readable
    python scripts/find_cities_needing_tariff_validation.py --json      # for a scheduled agent
    python scripts/find_cities_needing_tariff_validation.py --limit 25  # cap batch size
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")  # tariff_profiles.load() needs DATABASE_URL (Postgres, 2026-08-16 migration)

from backend.registry import cities as cities_registry  # noqa: E402
from backend.registry import global_cities as global_cities_registry  # noqa: E402
from backend.services import tariff_profiles  # noqa: E402

STALE_AFTER_DAYS = 90  # a fare structure this old is worth re-checking against current pricing


def _all_non_nyc_london_city_ids() -> set[str]:
    nyc_london = {c["id"] for c in cities_registry.list_cities()}  # has real trained fare models
    return {c["city_id"] for c in global_cities_registry.list_cities()} - nyc_london


def worklist() -> list[dict]:
    tariff_profiles.load()  # fresh read -- this worklist must reflect the live table, not a stale cache
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=STALE_AFTER_DAYS)
    items = []
    for city_id in sorted(_all_non_nyc_london_city_ids()):
        profile = tariff_profiles.get(city_id)
        if profile is None:
            items.append({"city_id": city_id, "reason": "missing"})
            continue
        if profile.validation_method is None:
            items.append({"city_id": city_id, "reason": "never_evidence_validated"})
            continue
        if profile.validated_at is None:
            items.append({"city_id": city_id, "reason": "never_evidence_validated"})
            continue
        validated_at = datetime.fromisoformat(profile.validated_at)
        if validated_at.tzinfo is None:
            validated_at = validated_at.replace(tzinfo=timezone.utc)
        if validated_at < stale_cutoff:
            items.append({"city_id": city_id, "reason": "stale", "validated_at": profile.validated_at})
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    items = worklist()
    if args.limit:
        items = items[: args.limit]

    if args.json:
        print(json.dumps(items, indent=2))
        return

    by_reason: dict[str, int] = {}
    for item in items:
        by_reason[item["reason"]] = by_reason.get(item["reason"], 0) + 1
    print(f"{len(items)} cities need a validate_tariff_city.py pass:")
    for reason, count in sorted(by_reason.items()):
        print(f"  {reason}: {count}")


def demo() -> None:
    items = worklist()
    assert isinstance(items, list)
    assert all("city_id" in item and "reason" in item for item in items)
    assert all(item["reason"] in ("missing", "never_evidence_validated", "stale") for item in items)
    print(f"find_cities_needing_tariff_validation demo OK: {len(items)} cities pending")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        main()
