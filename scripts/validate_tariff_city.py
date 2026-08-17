"""CLI wrapper for offline/batch evidence-grounded tariff regeneration
(ADR-011 extension, 2026-08-16). The actual propose/validate/confidence
logic lives in `backend/services/tariff_enrichment.py` -- shared with the
live on-demand WS path (`WS /api/cities/{city_id}/tariff/enrich`) so the two
never drift apart. This script is just the offline batch-run entry point:
give it a city_id and a pre-gathered evidence file (from a web-search pass),
it runs the pipeline once and prints the result instead of streaming it.

Usage:
    python scripts/validate_tariff_city.py mumbai --evidence evidence/mumbai.json
    python scripts/validate_tariff_city.py mumbai --evidence evidence/mumbai.json --dry-run

Evidence file format (list, [] is valid -- means "searched, found nothing usable"):
    [{"query": "Uber Mumbai fare per km 2025", "source": "reddit.com/r/mumbai",
      "url": "https://...", "snippet": "UberGo base fare is around Rs 40-60..."}]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from backend.services.tariff_enrichment import enrich_profile_streaming  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("city_id")
    parser.add_argument("--evidence", required=True, help="path to evidence JSON file (a list; [] is valid)")
    parser.add_argument("--dry-run", action="store_true", help="print the profile instead of writing it")
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))

    result = None
    for step in enrich_profile_streaming(args.city_id, evidence, persist=not args.dry_run):
        if step["type"] == "status":
            print(f"... {step['message']}", file=sys.stderr)
        elif step["type"] == "error":
            sys.exit(f"[skip] {args.city_id!r}: {step['message']}")
        elif step["type"] == "result":
            result = step["profile"]

    if result is None:
        sys.exit(f"[skip] {args.city_id!r}: no result produced")

    if args.dry_run:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"[ok] {result['city_id']}: {result['currency']} base={result['base_fare']} per_km={result['per_km']} "
          f"per_min={result['per_min']} min_fare={result['min_fare']} confidence={result['confidence']} "
          f"method={result['validation_method']}")


if __name__ == "__main__":
    main()
