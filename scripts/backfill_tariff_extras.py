"""Deterministic, offline agentic backfill for the tariff-profile fields no
generation pass has ever populated (ADR-011 follow-up): peak_multiplier,
surge_multiplier, booking_fee, platform_fee, tolls, vehicle_multiplier --
added to the schema by tariff_profiles.py's OPTIONAL_COLUMNS migration but
never asked for by generate_tariff_profile.py, so every existing row has
them NULL (TariffCard.tsx correctly renders that as "--").

Loops deterministically over city_tariff_profiles ordered by city_id -- a
plain for loop, not a free-roaming agent -- skipping any row already
backfilled (extras_backfilled_at IS NOT NULL -- a dedicated completion
marker, not a data field, since a city can honestly have none of these
fields set and that must not look like "never processed"), so a re-run only
touches what's still missing (same restart-safe pattern as
geocode_global_cities.py). One
grounded LLM call per city, reusing that city's own already-generated
base_fare/per_km/per_min/min_fare/currency/notes as context -- same "LLM as
knowledge source, not calculator" contract as generate_tariff_profile.py.
Never fabricates a default: a market that genuinely has no such fee/
multiplier gets that field left None, still rendering as "--", never a fake
dashboard number.

surge_multiplier is safe to fill because pricing_engine.py's
_base_fare_tariff now gates it on real demand pressure crossing
_SURGE_ACTIVE_THRESHOLD before applying it -- filling this field no longer
means a permanent fare markup (see git history for the pre-fix behavior).

Usage:
    python scripts/backfill_tariff_extras.py             # every profile still missing these fields
    python scripts/backfill_tariff_extras.py --limit 5    # pilot run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "rag"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from backend.services import global_geography_service  # noqa: E402
from backend.services.tariff_profiles import TABLE_NAME, TariffProfile, WAREHOUSE_PATH, upsert  # noqa: E402
from llm_client import chat_completion  # noqa: E402

_MODEL = "gpt-5.4-nano"

_PROMPT_TEMPLATE = """You previously calibrated this linear fare structure for {city_name}, {country_name} ({country_code}) in {currency}:
  base fare: {base_fare} {currency}
  distance rate: {per_km} {currency}/km
  time rate: {per_min} {currency}/min
  minimum fare: {min_fare} {currency}
  night multiplier: {night_multiplier}
  your own notes: {notes}

Now, using your real-world knowledge of {city_name}'s actual ride-hailing/taxi market (Uber, Ola,
local operators, auto-rickshaws/taxis as applicable), fill in the REMAINING fare-structure details.
Use null for anything this specific market genuinely does not have -- do not invent a fee or
multiplier just to fill a field. Reason about {city_name} specifically, not a generic default.

Respond with ONLY a JSON object, no prose, no markdown fences:
{{
  "peak_multiplier": <number > 1.0, this market's typical scheduled peak-hour multiplier, or null if it has none>,
  "surge_multiplier": <number > 1.0, this market's typical surge-pricing ceiling during real demand spikes, or null if it has no surge pricing>,
  "booking_fee": <number >= 0 in {currency}, a flat per-ride booking/dispatch fee, or null if none>,
  "platform_fee": <number >= 0 in {currency}, a flat platform/service fee separate from booking_fee, or null if none>,
  "tolls": <number >= 0 in {currency}, a typical flat toll passthrough for a city-average ride, or null if not applicable>,
  "vehicle_multiplier": <number > 0, a city-wide multiplier for this market's vehicle cost/import-tariff premium relative to a typical baseline (1.0 = no premium), or null if not distinct from 1.0>,
  "confidence": <number 0-1, your confidence in these figures>,
  "notes": "<one paragraph: what you're reasoning from and any caveat>"
}}
"""

_NUMERIC_FIELDS = (
    "peak_multiplier", "surge_multiplier", "booking_fee", "platform_fee", "tolls", "vehicle_multiplier",
)
_MULTIPLIER_FIELDS = ("peak_multiplier", "surge_multiplier", "vehicle_multiplier")
_FEE_FIELDS = ("booking_fee", "platform_fee", "tolls")


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rstrip("`").strip()
    return json.loads(text)


def _pending_profiles(limit: int | None) -> list[TariffProfile]:
    """Every city_tariff_profiles row still missing the extra fields,
    ordered by city_id -- deterministic, restart-safe.

    Sentinel is extras_backfilled_at, NOT peak_multiplier: a city can
    honestly have no peak/surge pricing at all, so peak_multiplier IS NULL
    is indistinguishable from "never backfilled" (this caused 250 already-
    processed cities to re-queue on every run -- see tariff_profiles.py's
    OPTIONAL_COLUMNS comment). extras_backfilled_at only ever means "the
    backfill pass has run for this row", independent of what it found."""
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        columns = [r[0] for r in con.execute(f"DESCRIBE {TABLE_NAME}").fetchall()]
        rows = con.execute(
            f"SELECT {', '.join(columns)} FROM {TABLE_NAME} WHERE extras_backfilled_at IS NULL ORDER BY city_id"
            + (f" LIMIT {int(limit)}" if limit else "")
        ).fetchall()
    finally:
        con.close()
    profiles = []
    for row in rows:
        data = {k: v for k, v in zip(columns, row) if v is not None}
        data["generated_at"] = str(data.get("generated_at"))
        for date_col in ("effective_from", "extras_backfilled_at"):
            if data.get(date_col) is not None:
                data[date_col] = str(data[date_col])
        profiles.append(TariffProfile(**data))
    return profiles


def backfill_one(profile: TariffProfile) -> TariffProfile | None:
    city = global_geography_service.get_city_profile(profile.city_id)
    city_name = city["city"] if city else profile.city_id
    country_name = (city.get("country") if city else None) or ""
    country_code = (city.get("country_code") if city else None) or ""

    prompt = _PROMPT_TEMPLATE.format(
        city_name=city_name, country_name=country_name, country_code=country_code,
        currency=profile.currency, base_fare=profile.base_fare, per_km=profile.per_km,
        per_min=profile.per_min, min_fare=profile.min_fare, night_multiplier=profile.night_multiplier,
        notes=profile.notes,
    )

    resp = chat_completion(
        model=_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2, max_completion_tokens=400,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = _parse_json_response(raw)
    except json.JSONDecodeError as exc:
        print(f"[skip] {profile.city_id!r}: LLM response not valid JSON: {exc}\n{raw!r}", file=sys.stderr)
        return None

    if "confidence" not in data or "notes" not in data or not str(data.get("notes", "")).strip():
        print(f"[skip] {profile.city_id!r}: response missing confidence/notes", file=sys.stderr)
        return None

    updates: dict[str, float | None] = {}
    for field in _NUMERIC_FIELDS:
        value = data.get(field)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            print(f"[skip] {profile.city_id!r}: {field}={value!r} not numeric", file=sys.stderr)
            return None
        if field in _MULTIPLIER_FIELDS and value <= 0:
            print(f"[skip] {profile.city_id!r}: {field}={value} must be > 0", file=sys.stderr)
            return None
        if field in _FEE_FIELDS and value < 0:
            print(f"[skip] {profile.city_id!r}: {field}={value} must be >= 0", file=sys.stderr)
            return None
        updates[field] = value

    # Weakest-link confidence (pricing_engine.compute_fare's own convention):
    # adding a less-certain component should never make the overall profile
    # look MORE trustworthy than its original fare-structure generation was.
    merged_confidence = min(profile.confidence, float(data["confidence"]))
    merged_notes = f"{profile.notes} | extras: {str(data['notes']).strip()}"

    for field, value in updates.items():
        setattr(profile, field, value)
    profile.confidence = merged_confidence
    profile.notes = merged_notes
    # Stamped unconditionally -- even when `updates` is empty (a city can
    # honestly have none of these fields), this row is done, never pending
    # again. See _pending_profiles()'s docstring for why this can't be
    # peak_multiplier itself.
    profile.extras_backfilled_at = datetime.now(timezone.utc).isoformat()
    return profile


def main(limit: int | None) -> None:
    pending = _pending_profiles(limit)
    print(f"{len(pending)} profile(s) pending extras backfill")
    ok, skipped = 0, 0
    for profile in pending:
        result = backfill_one(profile)
        if result is None:
            skipped += 1
            continue
        upsert(result)
        ok += 1
        filled = {f: getattr(result, f) for f in _NUMERIC_FIELDS if getattr(result, f) is not None}
        print(f"[ok] {result.city_id}: {filled}")
    print(f"\nDone: {ok} updated, {skipped} skipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(args.limit)
