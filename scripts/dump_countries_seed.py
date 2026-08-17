"""Regenerates dbt_project/seeds/countries.csv from GeoNames' countryInfoJSON
-- the same free, no-extra-dependency source backend/services/
global_geography_service.py already uses for per-country currency lookups
(ADR-008 pattern). Offline, one-shot; never called from a request path.

The seed used to be hand-maintained at 2 rows (nyc/london's own countries,
US/GB) from when this repo had exactly 2 onboarded cities. Once SPEC-016's
519-city global_cities registry landed (spanning 45 countries), that 2-row
table silently made every other real, resolvable country report
`supported: false` regardless of global_cities coverage (found 2026-08-16).
Seeding the full ~250-country universe here, with `supported` always derived
at query time (backend/registry/countries.py), means this file never needs
touching again as global_cities grows into new countries.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from backend.services import geonames_service  # noqa: E402

OUT_PATH = REPO_ROOT / "dbt_project" / "seeds" / "countries.csv"


def main() -> None:
    countries = geonames_service.get_all_countries()
    rows = sorted(
        {(c["iso2"], c["name"]) for c in countries if c.get("iso2") and c.get("name")}
    )
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["iso_code", "name"])
        writer.writerows(rows)
    print(f"wrote {len(rows)} countries to {OUT_PATH}")


if __name__ == "__main__":
    main()
