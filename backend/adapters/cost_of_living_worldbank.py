"""Real purchasing-power lookup via the World Bank Open Data API -- free, no
API key required (ADR-008 $0-budget pattern). Used to scale NYC's real
fare-per-mile rate into an honest `modeled_estimate` for any other country
(`backend/services/estimation_service.py`), never presented as a real fare
survey -- a single macroeconomic ratio, not a measured local taxi rate.

Indicator PA.NUS.PPP is the PPP conversion factor (LCU per international $),
published annually; the API returns several recent years per country and we
take the most recent one with a non-null value.

Observed in testing: api.worldbank.org has occasionally been slow/unreachable
(read timeouts even at 20s, while its own base domain resolves quickly) --
this is a real-world reliability characteristic of that specific API, not a
bug here. `fetch()` degrades honestly to `basis="unavailable"` on any
timeout/failure, same discipline as every other adapter; callers must treat
a `modeled_estimate` fare as one covariate that can legitimately be missing.
"""
from __future__ import annotations

from functools import lru_cache

import httpx
from loguru import logger

from backend.predictors.base import PredictionResult

_URL = "https://api.worldbank.org/v2/country/{country}/indicator/PA.NUS.PPP"


@lru_cache(maxsize=256)
def _cached_fetch(country_code: str) -> PredictionResult:
    try:
        resp = httpx.get(
            _URL.format(country=country_code),
            params={"format": "json", "per_page": 10, "mrnev": 1},
            timeout=5.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else None
        if not rows:
            logger.warning("cost_of_living_worldbank step=fetch no_rows country_code={}", country_code)
            return PredictionResult(
                value=None, unit=None, basis="unavailable", source="worldbank_ppp",
                reason=f"no PPP conversion factor published for country_code={country_code!r}",
            )
        row = next((r for r in rows if r.get("value") is not None), None)
        if row is None:
            logger.warning("cost_of_living_worldbank step=fetch no_non_null_value country_code={}", country_code)
            return PredictionResult(
                value=None, unit=None, basis="unavailable", source="worldbank_ppp",
                reason=f"no non-null PPP conversion factor for country_code={country_code!r}",
            )
        return PredictionResult(
            value=float(row["value"]), unit="LCU_per_intl_dollar", basis="computed",
            source="worldbank_ppp", reason=None,
        )
    except Exception as exc:  # noqa: BLE001 -- network/API failure degrades honestly upstream
        logger.warning("cost_of_living_worldbank step=fetch failed country_code={} reason={}", country_code, exc)
        return PredictionResult(
            value=None, unit=None, basis="unavailable", source="worldbank_ppp",
            reason=f"World Bank Open Data request failed for country_code={country_code!r}: {exc}",
        )


def fetch(country_code: str) -> PredictionResult:
    return _cached_fetch(country_code.upper())


def demo() -> None:
    us = fetch("US")
    assert us.basis in ("computed", "unavailable")
    print(f"US PPP conversion factor: {us.value} ({us.basis})")


if __name__ == "__main__":
    demo()
