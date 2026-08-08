"""Vehicle profiles -- data, not conditionals (ADR-007).

Loads `dbt_project/seeds/vehicle_profiles.csv` once (same pattern as
`model_service.py`'s startup artifact loading, and `zones.py` reading
`zone_centroids.csv` directly rather than requiring `dbt seed` to have run
first -- this is static reference data, not a query result). Every
vehicle-sensitive predictor multiplies its base computation by the resolved
`VehicleProfile`'s factors instead of a hardcoded `if vehicle == "suv"`
branch.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.predictors.base import VehicleProfile

SEED_PATH = Path(__file__).resolve().parents[2] / "dbt_project" / "seeds" / "vehicle_profiles.csv"

_profiles: dict[str, VehicleProfile] = {}


def load(path: Path = SEED_PATH) -> None:
    global _profiles
    df = pd.read_csv(path)
    _profiles = {
        str(row.vehicle_class): VehicleProfile(
            vehicle_class=str(row.vehicle_class),
            capacity=int(row.capacity),
            base_fare_factor=float(row.base_fare_factor),
            distance_rate_factor=float(row.distance_rate_factor),
            time_rate_factor=float(row.time_rate_factor),
            minimum_fare_factor=float(row.minimum_fare_factor),
            traffic_sensitivity=float(row.traffic_sensitivity),
            demand_sensitivity=float(row.demand_sensitivity),
            availability_prior=float(row.availability_prior),
            emission_factor=float(row.emission_factor),
            comfort_score=float(row.comfort_score),
        )
        for row in df.itertuples()
    }


def resolve(vehicle_type: str) -> VehicleProfile | None:
    return _profiles.get(vehicle_type.strip().lower())


def list_vehicle_classes() -> list[str]:
    return sorted(_profiles.keys())
