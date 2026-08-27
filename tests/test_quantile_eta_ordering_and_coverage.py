"""Phase 7 test: p10 <= p50 <= p90 ordering (mostly) holds, and prediction
interval coverage is actually computed from held-out predictions -- not
hardcoded to some plausible-looking constant.
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models"))

from congestion.build_features import DEFAULT_DB_PATH, build_features  # noqa: E402
from eta.train_quantile_eta import train_and_save  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def metadata():
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        df = build_features(con, sample_rows=20_000)
    finally:
        con.close()
    return train_and_save(df=df)


def test_quantile_ordering_mostly_holds(metadata):
    # A handful of crossings between independently-trained quantile models is
    # a known, real phenomenon -- assert it's rare (<5% of test rows), not
    # asserting a fabricated zero.
    n_test = metadata["n_rows"]["test"]
    violations = metadata["ordering_violations_p10_p50_p90"]
    assert violations / n_test < 0.05, f"too many p10<=p50<=p90 ordering violations: {violations}/{n_test}"


def test_coverage_is_measured_not_hardcoded(metadata):
    cov = metadata["prediction_interval_coverage"]
    assert cov["n_test_rows"] > 0
    assert 0.0 <= cov["measured_p10_p90_coverage"] <= 1.0
    # A hardcoded/fabricated "0.80 exactly" would be suspicious; real
    # empirical coverage on a finite sample essentially never lands on an
    # exact round number -- this is a smoke check that the value came from
    # real predictions, not a literal.
    assert cov["measured_p10_p90_coverage"] != cov["nominal"]


def test_pinball_losses_are_real_numbers(metadata):
    for name, m in metadata["metrics"].items():  # noqa: PERF102
        assert np.isfinite(m["pinball_loss"])
        assert m["pinball_loss"] >= 0
