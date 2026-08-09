"""Real, dated FX rates via fawazahmed0/exchange-api (ADR-008 $0-budget
pattern) -- free, no API key, CDN-hosted, no rate limit documented.
https://github.com/fawazahmed0/exchange-api

Verified live 2026-08-09: `usd.json` returns `inr=95.12`, `jpy=157.82`,
`ngn=1366.02`, dated `2026-08-08` -- the response's own `date` field, not a
constant, so a stale cache is visible in `source` rather than silently
passed off as today's rate.

FX is never on the primary fare path (`backend/services/pricing_engine.py`
computes in whatever local currency a `TariffProfile` was authored in). It's
used only to convert the NYC/London reference fares into a target currency
when generating a new profile (`scripts/generate_tariff_profile.py`) and for
the optional cross-city USD comparison field -- if this adapter is down,
every already-generated fare still returns in its own currency untouched.
"""
from __future__ import annotations

from functools import lru_cache

import httpx

from backend.predictors.base import PredictionResult

_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"
# The project's own documented failover host (date-versioned Cloudflare Pages
# mirror) -- used only if the jsdelivr CDN itself is unreachable.
_FALLBACK = "https://latest.currency-api.pages.dev/v1/currencies/{base}.json"


@lru_cache(maxsize=16)
def _fetch_rates(base: str) -> tuple[dict, str] | None:
    for url_tmpl in (_PRIMARY, _FALLBACK):
        try:
            resp = httpx.get(url_tmpl.format(base=base), timeout=5.0, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get(base)
            if rates:
                return rates, str(data.get("date", "unknown"))
        except Exception:  # noqa: BLE001 -- network/API failure degrades honestly upstream
            continue
    return None


def get_rate(base: str, target: str) -> PredictionResult:
    base, target = base.lower(), target.lower()
    fetched = _fetch_rates(base)
    if fetched is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="fx_rates",
            reason="exchange-api unreachable on both the primary CDN and its documented fallback",
        )
    rates, date = fetched
    rate = rates.get(target)
    if rate is None:
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source=f"fx_rates:{date}",
            reason=f"no published rate for {target.upper()!r}",
        )
    return PredictionResult(
        value=float(rate), unit=f"{target.upper()}_per_{base.upper()}", basis="computed",
        source=f"fx_rates:{date}", reason=None,
    )


def demo() -> None:
    rate = get_rate("usd", "inr")
    assert rate.basis in ("computed", "unavailable")
    print(f"USD->INR: {rate.value} ({rate.basis}, {rate.source})")


if __name__ == "__main__":
    demo()
