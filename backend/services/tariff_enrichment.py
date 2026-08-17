"""On-demand tariff enrichment (2026-08-16, extends ADR-011 -- see the
module docstring in `tariff_profiles.py` for how `city_tariff_profiles`
moved to Postgres and why).

The original plan was a one-time bulk backfill of all 517 non-NYC/London
cities. Instead: fill lazily, when a user actually opens that city's page,
not before -- most of the 519-city registry will never be looked at, so
computing a profile for all of them up front is wasted LLM spend for
numbers nobody will ever see. `backend/routers/cities.py`'s
`WS /api/cities/{city_id}/tariff/enrich` calls `enrich_profile_streaming()`
below and forwards each yielded step to the browser in real time ("agent is
analyzing..." -> result), so the wait is visible instead of a silent spinner.

Deliberate exception to rule 8 ("no LLM call on a request path"), narrow and
documented rather than silent: this is the one place in the repo an LLM call
now happens on a live request path. It's still never on the HOT path (fare
lookups always read whatever's cached; this only fires once per city, the
first time anyone opens it, then never again for that city), and it's
serialized per-city (`_locks` below) so concurrent visitors to the same
never-opened city trigger exactly one DeepSeek round-trip, not N.

No live web search here -- that needs a real search API (Tavily key is
unset, see `.env`), so this path uses what's backend-native: the analytical
PPP-scaled anchor (`estimation_service.estimate_fare_per_mile`, a real
dataset + a real published macroeconomic index) plus DeepSeek reasoning
grounded in it. Same quality tier as `analytical_only`/`llm_only_fallback`
in the offline batch run -- honestly labeled as such, never as web-corroborated.
"""
from __future__ import annotations

import asyncio
import json
import queue
import sys
import threading
from collections.abc import Callable, Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "rag") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "rag"))

from backend.services import estimation_service, global_geography_service  # noqa: E402
from backend.services.tariff_profiles import TariffProfile, upsert  # noqa: E402
from llm_client import chat_completion  # noqa: E402

_MODEL = "deepseek-chat"
NYC_ANCHOR_CACHE = REPO_ROOT / "data" / "backups" / "nyc_fare_anchor_cache.json"
_CORE_FIELDS = ("base_fare", "per_km", "per_min", "min_fare")

_PROPOSE_TEMPLATE = """You are calibrating a ride-hailing fare estimator for {city_name}, country code {country_code}.

Real, measured reference point from this platform's own trip data -- a least-squares fit
over {n_sampled:,} real NYC ride-hailing trips (fare = total_amount, including tolls/tax/tip):
  base fare: ${base_fare_usd} USD
  distance rate: ${per_mile_usd} USD/mile (${per_mile_usd_per_km:.2f} USD/km)
  time rate: ${per_min_usd} USD/minute
  median total fare: ${median_fare_usd} USD
  effective minimum fare (5th percentile): ${min_fare_usd} USD

{evidence_block}

Using {evidence_instruction}, output a realistic fare structure for {city_name} in {currency}.
Do NOT default to a generic value that would fit any city in this region/currency zone --
if the evidence gives you a specific number or range, use it; only fall back to reasoned
estimation for fields the evidence doesn't cover, and say so plainly in "notes".

Respond with ONLY a JSON object, no prose, no markdown fences:
{{
  "currency": "{currency}",
  "base_fare": <number, {currency}>,
  "per_km": <number, {currency} per km>,
  "per_min": <number, {currency} per minute>,
  "min_fare": <number, {currency}>,
  "night_multiplier": <number, e.g. 1.25 for a typical night surcharge, 1.0 if none>,
  "airport_surcharge": <number, {currency}, 0 if none>,
  "field_citations": {{
    "base_fare": [<every literal number the evidence states for base fare, {currency}, [] if none>],
    "per_km": [<every literal per-km number the evidence states, {currency}, [] if none>],
    "per_min": [<every literal per-minute number the evidence states, {currency}, [] if none>],
    "min_fare": [<every literal minimum-fare number the evidence states, {currency}, [] if none>]
  }},
  "notes": "<one paragraph: what you're reasoning from -- and any caveat>"
}}

field_citations is an EXTRACTION task, not a judgment call: list the actual numbers the evidence
text contains for that field (there can be several, e.g. different vehicle tiers or conflicting
sources) -- do not summarize or round them, and leave a field's list empty if evidence never
states a number for it. This is what confidence will be computed from, not your opinion.
"""

_VALIDATE_TEMPLATE = """You proposed this fare structure for {city_name} ({currency}):
{proposed_json}

Here is the evidence you were given:
{evidence_block}

Check your own proposal against the evidence: does every number that the evidence actually
supports match what you proposed? If the evidence contradicts a number, fix it -- prefer the
most specific/recent/authoritative source over a generic or older one. If the evidence doesn't
cover a field, leave your original estimate. Re-verify field_citations too: fix any number you
mis-extracted the first time.

Respond with ONLY a JSON object, no prose, no markdown fences, same shape as before:
{{
  "currency": "{currency}",
  "base_fare": <number>, "per_km": <number>, "per_min": <number>, "min_fare": <number>,
  "night_multiplier": <number>, "airport_surcharge": <number>,
  "field_citations": {{"base_fare": [...], "per_km": [...], "per_min": [...], "min_fare": [...]}},
  "notes": "<final one-paragraph justification>"
}}
"""


def _parse_json_response(text: str) -> dict:
    import re

    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rstrip("`").strip()
    return json.loads(text)


def load_nyc_anchor() -> dict:
    if not NYC_ANCHOR_CACHE.exists():
        raise FileNotFoundError(
            f"NYC anchor cache missing at {NYC_ANCHOR_CACHE} -- run nyc_fare_anchor.fit_nyc_fare_anchor() once and cache it"
        )
    return json.loads(NYC_ANCHOR_CACHE.read_text(encoding="utf-8"))


def _analytical_evidence(country_code: str) -> dict | None:
    """NYC's real measured fare-per-mile, PPP-scaled -- see module docstring."""
    result = estimation_service.estimate_fare_per_mile(country_code)
    if result.basis == "unavailable" or result.value is None:
        return None
    per_km_usd = result.value / 1.609344
    return {
        "source": "computed: NYC real fare-per-mile x World Bank PPP ratio "
                   "(estimation_service.estimate_fare_per_mile, already used for cross-city demand estimation)",
        "url": None,
        "snippet": f"Analytical anchor (not web search): {result.reason} "
                   f"-> approximately ${per_km_usd:.2f} USD/km equivalent purchasing-power-adjusted rate. "
                   f"Convert to local currency and treat as an order-of-magnitude cross-check against "
                   f"any web-search evidence, not a substitute for a real published local rate.",
    }


def _format_evidence(evidence: list[dict]) -> str:
    if not evidence:
        return "No usable web evidence was found for this city."
    lines = ["Web search evidence gathered for this city:"]
    for i, item in enumerate(evidence, 1):
        source = item.get("source") or item.get("url") or "unknown source"
        lines.append(f"  {i}. [{source}] {item.get('snippet', '').strip()}")
    return "\n".join(lines)


def _field_confidence(chosen: float, citations: list[float]) -> float:
    """A real statistic, not a self-report -- see tariff_profiles.py's
    OPTIONAL_COLUMNS comment for why this replaced an LLM self-rating."""
    citations = [c for c in citations if isinstance(c, (int, float))]
    if not citations:
        return 0.15
    nearest = min(citations, key=lambda c: abs(c - chosen))
    rel_dev = 0.0 if nearest == chosen else min(abs(chosen - nearest) / max(abs(nearest), 1e-6), 1.0)
    if len(citations) > 1:
        mean_c = sum(citations) / len(citations)
        variance = sum((c - mean_c) ** 2 for c in citations) / len(citations)
        agreement_penalty = min((variance**0.5) / max(mean_c, 1e-6), 1.0)
    else:
        agreement_penalty = 0.2
    return max(0.1, min(0.97, 1.0 - rel_dev * 0.6 - agreement_penalty * 0.3))


def _confidence_from_citations(final: dict, has_web_evidence: bool) -> tuple[float, str, dict[str, float]]:
    citations = final.get("field_citations") or {}
    per_field = {
        field: _field_confidence(float(final[field]), citations.get(field, []))
        for field in _CORE_FIELDS
    }
    overall = round(sum(per_field.values()) / len(per_field), 2)
    n_cited = sum(1 for f in _CORE_FIELDS if citations.get(f))
    if n_cited == 0:
        method = "llm_only_fallback"
    elif not has_web_evidence:
        method = "analytical_only"
    elif n_cited >= 3 and overall >= 0.6:
        method = "web_search_corroborated"
    else:
        method = "web_search_partial"
    return overall, method, per_field


def enrich_profile_streaming(
    city_id: str, evidence: list[dict] | None = None, *, persist: bool = True,
) -> Generator[dict[str, Any], None, None]:
    """Yields `{"type": "status"|"error"|"result", ...}` steps as it goes, so
    a caller (the WS route) can forward real progress instead of a silent
    wait. Upserts the result to Postgres when `persist=True` (the WS path's
    default and whole point); pass `persist=False` for a preview run (the
    CLI's `--dry-run`) that must not touch the live table. Never raises;
    failures come out as a final `{"type": "error"}` yield so a WS handler
    can always end its stream cleanly instead of leaking a raw traceback to
    a client (same discipline as `chat.py`'s WS -- see its comment on why
    str(exc) never reaches a client)."""
    evidence = evidence or []
    try:
        yield {"type": "status", "message": f"Resolving {city_id}..."}
        profile = global_geography_service.get_city_profile(city_id)
        if profile is None:
            yield {"type": "error", "message": f"{city_id} is not a resolvable city"}
            return

        nyc_anchor = load_nyc_anchor()
        country_code = profile.get("country_code") or "US"
        currency = global_geography_service.get_currency_for_country(country_code)

        yield {"type": "status", "message": "Computing analytical anchor (NYC's real fare-per-mile, scaled by World Bank purchasing-power data)..."}
        has_web_evidence = bool(evidence)
        analytical = _analytical_evidence(country_code)
        all_evidence = evidence + ([analytical] if analytical else [])
        evidence_block = _format_evidence(all_evidence)
        evidence_instruction = (
            "the evidence above (including the computed analytical anchor) and your real-world knowledge "
            "of local ride-hailing/taxi markets"
            if all_evidence else
            "your real-world knowledge of local ride-hailing/taxi markets (no evidence, web or analytical, "
            "was available -- be conservative and say so in notes)"
        )

        yield {"type": "status", "message": f"Proposing a fare structure for {profile['city']}..."}
        propose_prompt = _PROPOSE_TEMPLATE.format(
            city_name=profile["city"], country_code=country_code, currency=currency,
            per_mile_usd_per_km=nyc_anchor["per_mile_usd"] / 1.609344,
            evidence_block=evidence_block, evidence_instruction=evidence_instruction,
            **nyc_anchor,
        )
        resp = chat_completion(model=_MODEL, messages=[{"role": "user", "content": propose_prompt}],
                                temperature=0.4, max_completion_tokens=700)
        proposed = _parse_json_response((resp.choices[0].message.content or "").strip())

        yield {"type": "status", "message": "Self-validating the proposal against the evidence..."}
        validate_prompt = _VALIDATE_TEMPLATE.format(
            city_name=profile["city"], currency=currency,
            proposed_json=json.dumps(proposed, indent=2), evidence_block=evidence_block,
        )
        resp = chat_completion(model=_MODEL, messages=[{"role": "user", "content": validate_prompt}],
                                temperature=0.2, max_completion_tokens=700)
        try:
            final = _parse_json_response((resp.choices[0].message.content or "").strip())
        except json.JSONDecodeError:
            final = proposed

        required = ("currency", "base_fare", "per_km", "per_min", "min_fare", "notes")
        missing = [k for k in required if k not in final]
        if missing or not final["notes"].strip() or final["currency"].upper() != currency.upper():
            yield {"type": "error", "message": "the agent's response didn't pass validation, try again"}
            return

        confidence, validation_method, per_field_confidence = _confidence_from_citations(final, has_web_evidence)
        sources = [{"source": e.get("source"), "url": e.get("url")} for e in all_evidence]

        result = TariffProfile(
            city_id=profile["city_id"], currency=currency.upper(),
            base_fare=float(final["base_fare"]), per_km=float(final["per_km"]), per_min=float(final["per_min"]),
            min_fare=float(final["min_fare"]), night_multiplier=float(final.get("night_multiplier", 1.0)),
            airport_surcharge=float(final.get("airport_surcharge", 0.0)),
            source="llm_anchored", generated_at=datetime.now(timezone.utc).isoformat(),
            model_id=_MODEL, confidence=confidence, notes=final["notes"].strip(),
            evidence_sources=json.dumps(sources), validation_method=validation_method,
            validated_at=datetime.now(timezone.utc).isoformat(),
        )
        if persist:
            upsert(result)
        from dataclasses import asdict

        yield {"type": "result", "profile": asdict(result), "per_field_confidence": per_field_confidence}
    except Exception as exc:  # noqa: BLE001 -- see docstring: this must never leak a raw traceback to a WS client
        logger.exception("tariff_enrichment.enrich_profile_streaming failed city_id={}", city_id)
        yield {"type": "error", "message": "something went wrong enriching this city's tariff data"}


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(city_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(city_id, threading.Lock())


def needs_enrichment(city_id: str) -> bool:
    """A city needs enrichment if it has no profile yet, or has one that
    was never evidence/analytically validated (the pre-2026-08-16 batch
    rows, still `validation_method IS NULL` until they're individually
    re-visited -- see `find_cities_needing_tariff_validation.py` for the
    equivalent offline-sweep definition this mirrors for a single city)."""
    from backend.services import tariff_profiles

    profile = tariff_profiles.get(city_id)
    return profile is None or profile.validation_method is None


async def stream_enrichment_over_websocket(
    websocket, city_id: str, evidence: list[dict] | None = None,
) -> None:
    """Runs `enrich_profile_streaming` (blocking: DeepSeek + Postgres calls)
    in a worker thread and forwards each yielded step to `websocket` as it
    happens, via a thread-safe queue -- keeps the event loop free for other
    connections while this one city's enrichment runs. Serialized per
    city_id (`_lock_for`) so N concurrent visitors to the same never-opened
    city trigger exactly one DeepSeek round-trip: the first caller runs it,
    the rest block on the lock and then immediately get the now-cached
    result via the normal `needs_enrichment`/`tariff_profiles.get` path
    instead of running it again."""
    from backend.services import tariff_profiles

    lock = _lock_for(city_id)
    got_lock = lock.acquire(blocking=False)
    if not got_lock:
        await websocket.send_json({"type": "status", "message": f"Another request is already analyzing {city_id}, waiting for it..."})
        await asyncio.to_thread(lock.acquire)
        lock.release()
        cached = tariff_profiles.get(city_id)
        if cached is not None:
            from dataclasses import asdict
            await websocket.send_json({"type": "result", "profile": asdict(cached), "cached": True})
        else:
            await websocket.send_json({"type": "error", "message": "enrichment did not complete"})
        return

    q: queue.Queue = queue.Queue()
    _SENTINEL = object()

    def worker() -> None:
        try:
            for item in enrich_profile_streaming(city_id, evidence):
                q.put(item)
        finally:
            q.put(_SENTINEL)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        while True:
            item = await asyncio.to_thread(q.get)
            if item is _SENTINEL:
                break
            await websocket.send_json(item)
    finally:
        lock.release()
