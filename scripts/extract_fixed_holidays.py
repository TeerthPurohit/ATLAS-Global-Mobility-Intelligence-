"""Extends holiday coverage past Nager.Date's 204 countries (notably: no
India) using the real global 2010-2019 calendar the user supplied
(`data/raw/day_public_and_school_holidays_2010_2019.csv`) -- but only for
holidays that are honestly extrapolable.

The source file is 5-15 years stale for this platform's actual 2024-2026
date range, so it can't be used directly as "is this date a holiday" the
way `holidays_nager.py` uses Nager's live, year-correct calendar. What IS
honest: a (country, month, day) that was flagged `holiday=1` in EVERY one
of the 10 years present is, by construction, a fixed-date holiday (a
floating holiday like Eid or a lunar new year would almost never land on
the same calendar date 10 years running) -- New Year's Day, a fixed
Independence Day, etc. Those generalize to any year. Floating holidays are
silently excluded by this same rule, not approximated.

Scoped to countries Nager.Date doesn't cover at all (rules.md rule 7:
don't duplicate/override a source that's already correct and live).
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from backend.services import geonames_service  # noqa: E402

SOURCE_CSV = REPO_ROOT / "data" / "raw" / "day_public_and_school_holidays_2010_2019.csv"
OUT_PATH = REPO_ROOT / "dbt_project" / "seeds" / "fixed_holidays_extended.csv"
NAGER_COUNTRIES_URL = "https://date.nager.at/api/v3/AvailableCountries"


def _nager_covered_iso2() -> set[str]:
    resp = httpx.get(NAGER_COUNTRIES_URL, timeout=10.0)
    resp.raise_for_status()
    return {row["countryCode"] for row in resp.json()}


def _iso3_to_iso2_map() -> dict[str, str]:
    return {c["iso3"]: c["iso2"] for c in geonames_service.get_all_countries() if c.get("iso3") and c.get("iso2")}


def extract() -> pd.DataFrame:
    nager_covered = _nager_covered_iso2()
    iso3_to_iso2 = _iso3_to_iso2_map()

    df = pd.read_csv(SOURCE_CSV, parse_dates=["Date"], usecols=["ISO3", "Date", "Year", "holiday"])
    n_years_present = df.groupby("ISO3")["Year"].nunique()

    rows = []
    for iso3, group in df.groupby("ISO3"):
        iso2 = iso3_to_iso2.get(iso3)
        if iso2 is None or iso2 in nager_covered:
            continue  # Nager already covers this country live -- don't shadow it
        n_years = n_years_present[iso3]
        month_day = group["Date"].dt.strftime("%m-%d")
        holiday_rate = group.assign(month_day=month_day).groupby("month_day")["holiday"].sum()
        fixed = holiday_rate[holiday_rate == n_years]  # holiday=1 in literally every year present
        for md in fixed.index:
            month, day = md.split("-")
            rows.append({"country_code": iso2, "month": int(month), "day": int(day), "source_years": n_years})

    return pd.DataFrame(rows).sort_values(["country_code", "month", "day"]).reset_index(drop=True)


def demo() -> None:
    result = extract()
    assert not result.empty
    assert "IN" in result["country_code"].values, "expected India (not covered by Nager.Date) in the extended set"
    assert result["month"].between(1, 12).all() and result["day"].between(1, 31).all()
    print(f"extract_fixed_holidays demo OK: {len(result)} rows, {result['country_code'].nunique()} countries")


if __name__ == "__main__":
    result = extract()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(result)} fixed-date holiday rows for {result['country_code'].nunique()} countries "
          f"(not covered by Nager.Date) to {OUT_PATH}")
    demo()