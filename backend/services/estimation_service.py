"""Estimation service (SPEC-015 FR-5) -- thin backend wrapper around
`models/cross_city_estimation/estimate.py`.

Provides tier-2 demand estimation for cities with population covariates but no
real trip-level model, returning structured `PredictionResult` objects with
`basis="modeled_estimate"` and an honest, explicit reason string explaining
the 2-reference-point scaling basis.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.predictors.base import PredictionResult  # noqa: E402
from models.cross_city_estimation.estimate import estimate_demand_per_capita  # noqa: E402

logger = logging.getLogger(__name__)


def estimate_city_demand(city_id: str, population: int, density: float | None = None) -> PredictionResult:
    """Estimate daily demand volume for a city using NYC/London demand-per-capita scaling.

    Always returns `basis="modeled_estimate"` with a clear non-validated reason,
    never `computed` (rule 2 / ADR-007 discipline).
    """
    if population <= 0:
        return PredictionResult(
            value=None,
            unit="trips/day",
            basis="unavailable",
            source="cross_city_estimation",
            reason=f"population covariate must be positive, got {population}",
        )

    val, reason = estimate_demand_per_capita(population, density)
    logger.info("estimation_service: city_id=%s population=%d -> estimate=%.1f", city_id, population, val)
    return PredictionResult(
        value=val,
        unit="trips/day",
        basis="modeled_estimate",
        source="cross_city_estimation (NYC/London 2-point reference scaling)",
        reason=reason,
    )
