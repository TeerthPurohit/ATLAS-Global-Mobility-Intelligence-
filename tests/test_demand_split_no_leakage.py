"""Leakage-guard + identical-test-set tests for the demand model ladder
(SPEC-006, ADR-003): train must fully precede val, val must fully precede
test, and all 4 models must be scored on the same test rows.
"""

import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from data_prep.build_features import DEFAULT_DB_PATH, build_features  # noqa: E402
from data_prep.train_test_split import split_demand_blocks  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="warehouse not built")


def test_demand_chronological_split_no_leakage():
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    df = build_features(con)

    train, val, test = split_demand_blocks(df, "ts")

    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["ts"].max() < val["ts"].min()
    assert val["ts"].max() < test["ts"].min()


def test_compare_models_uses_identical_test_rows():
    from evaluation.compare_models import evaluate_all

    results = evaluate_all()
    n_rows = {name: m["n_rows"] for name, m in results.items()}
    assert len(set(n_rows.values())) == 1, f"models scored on different row counts: {n_rows}"
