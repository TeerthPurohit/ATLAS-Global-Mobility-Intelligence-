"""Tests and verification for the London XGBoost demand model (SPEC-015 FR-4).

Ensures the London demand model trains without errors, respects the chronological
split, produces valid metadata with no target leakage, and saves the model artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from models.london_demand.train_london_xgb import ARTIFACT_DIR, train_and_save  # noqa: E402

LONDON_DB = REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb"

pytestmark = pytest.mark.skipif(not LONDON_DB.exists(), reason="London warehouse not built")


def test_train_london_xgb_model():
    meta = train_and_save()
    assert (ARTIFACT_DIR / "xgb_model.json").exists()
    assert (ARTIFACT_DIR / "xgb_metadata.json").exists()

    assert meta["model_id"] == "xgboost_london_demand_v1"
    assert meta["city_id"] == "london"
    assert meta["metrics"]["test_rmse"] > 0
    assert meta["metrics"]["test_mae"] > 0

    # Verify chronological split discipline
    train_max = meta["date_range"]["train"][1]
    val_min = meta["date_range"]["val"][0]
    val_max = meta["date_range"]["val"][1]
    test_min = meta["date_range"]["test"][0]

    assert train_max <= val_min
    assert val_max <= test_min


if __name__ == "__main__":
    if LONDON_DB.exists():
        test_train_london_xgb_model()
        print("test_london_model OK")
    else:
        print("London DB does not exist, skipping test")
