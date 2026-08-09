"""One-time, offline LLM call per city (ADR-011, rule 8: never on a request
path). Generates a `TariffProfile` -- a small linear fare structure (base
fare, per-km, per-min, minimum fare) in the city's OWN currency -- anchored
on NYC's real, measured fare regression (scripts/nyc_fare_anchor.py), and
writes it to the `city_tariff_profiles` table
(backend/services/tariff_profiles.py).

The LLM never computes a price. It supplies parameters no dataset in this
repo has (what does a Mumbai auto-rickshaw/Ola ride actually cost) --
`pricing_engine.py` does all the arithmetic from there. This is what keeps
rules.md rule 1 intact: LLM-as-knowledge-source, not LLM-as-calculator.

Usage:
    python scripts/generate_tariff_profile.py mumbai jaipur delhi kolkata tokyo lagos

`city_id` is anything `global_geography_service.get_city_profile()` can
resolve -- a registered city_id, a GeoNames id, or a free-text place name.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "rag"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from backend.services import global_geography_service  # noqa: E402
from backend.services.tariff_profiles import TariffProfile, upsert  # noqa: E402
from llm_client import chat_completion  # noqa: E402
from nyc_fare_anchor import fit_nyc_fare_anchor  # noqa: E402

_MODEL = "gpt-5.4-nano"

_PROMPT_TEMPLATE = """You are calibrating a ride-hailing fare estimator for {city_name}, {country_name} ({country_code}).

Real, measured reference point from this platform's own trip data -- a least-squares fit
over {n_sampled:,} real NYC ride-hailing trips (fare = total_amount, including tolls/tax/tip):
  base fare: ${base_fare_usd} USD
  distance rate: ${per_mile_usd} USD/mile (${per_mile_usd_per_km:.2f} USD/km)
  time rate: ${per_min_usd} USD/minute
  median total fare: ${median_fare_usd} USD
  effective minimum fare (5th percentile): ${min_fare_usd} USD

Using your real-world knowledge of {city_name}'s actual ride-hailing/taxi market (Uber, Ola,
local operators, auto-rickshaws/taxis as applicable), output a realistic fare structure for
{city_name} in {currency}. Do NOT just convert the NYC numbers at the exchange rate -- local
markets differ hugely in base fare, per-km rate, and minimum fare relative to purchasing
power and local competition; reason about {city_name} specifically.

Respond with ONLY a JSON object, no prose, no markdown fences:
{{
  "currency": "{currency}",
  "base_fare": <number, {currency}>,
  "per_km": <number, {currency} per km>,
  "per_min": <number, {currency} per minute>,
  "min_fare": <number, {currency}>,
  "night_multiplier": <number, e.g. 1.25 for a typical night surcharge, 1.0 if none>,
  "airport_surcharge": <number, {currency}, 0 if none>,
  "confidence": <number 0-1, your confidence in these figures>,
  "notes": "<one paragraph: what you're reasoning from and any caveat>"
}}
"""


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rstrip("`").strip()
    return json.loads(text)


def generate_profile(city_id: str, nyc_anchor: dict) -> TariffProfile | None:
    profile = global_geography_service.get_city_profile(city_id)
    if profile is None:
        print(f"[skip] {city_id!r}: not resolvable via global geography", file=sys.stderr)
        return None

    country_code = profile.get("country_code") or "US"
    currency = global_geography_service.get_currency_for_country(country_code)
    prompt = _PROMPT_TEMPLATE.format(
        city_name=profile["city"], country_name=profile.get("country") or country_code,
        country_code=country_code, currency=currency,
        per_mile_usd_per_km=nyc_anchor["per_mile_usd"] / 1.609344,
        **nyc_anchor,
    )

    resp = chat_completion(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_completion_tokens=500,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = _parse_json_response(raw)
    except json.JSONDecodeError as exc:
        print(f"[skip] {city_id!r}: LLM response not valid JSON: {exc}\n{raw!r}", file=sys.stderr)
        return None

    required = ("currency", "base_fare", "per_km", "per_min", "min_fare", "confidence", "notes")
    missing = [k for k in required if k not in data]
    if missing:
        print(f"[skip] {city_id!r}: response missing {missing}", file=sys.stderr)
        return None
    if not data["notes"].strip():
        print(f"[skip] {city_id!r}: no justification in response, rejecting", file=sys.stderr)
        return None
    if data["currency"].upper() != currency.upper():
        print(f"[skip] {city_id!r}: response currency {data['currency']!r} != resolved {currency!r}", file=sys.stderr)
        return None

    return TariffProfile(
        city_id=profile["city_id"], currency=currency.upper(),
        base_fare=float(data["base_fare"]), per_km=float(data["per_km"]), per_min=float(data["per_min"]),
        min_fare=float(data["min_fare"]), night_multiplier=float(data.get("night_multiplier", 1.0)),
        airport_surcharge=float(data.get("airport_surcharge", 0.0)),
        source="llm_anchored", generated_at=datetime.now(timezone.utc).isoformat(),
        model_id=_MODEL, confidence=float(data["confidence"]), notes=data["notes"].strip(),
    )


def main(city_ids: list[str]) -> None:
    if not city_ids:
        print("usage: python scripts/generate_tariff_profile.py <city_id> [<city_id> ...]", file=sys.stderr)
        sys.exit(1)
    nyc_anchor = fit_nyc_fare_anchor()
    print(f"NYC anchor: {nyc_anchor}")
    for city_id in city_ids:
        profile = generate_profile(city_id, nyc_anchor)
        if profile is None:
            continue
        upsert(profile)
        print(f"[ok] {profile.city_id}: {profile.currency} base={profile.base_fare} per_km={profile.per_km} "
              f"per_min={profile.per_min} min_fare={profile.min_fare} confidence={profile.confidence}")


if __name__ == "__main__":
    main(sys.argv[1:])
