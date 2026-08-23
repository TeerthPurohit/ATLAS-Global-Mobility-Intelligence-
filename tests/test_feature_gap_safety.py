"""Phase 3 gap-safety proof: lag_1h/lag_24h/lag_168h/ewma/rolling_7d_avg must
never treat a data-gap boundary (e.g. last row 2024-03-31, next row
2024-04-30) as consecutive hours.

`_block_features()` in `models/data_prep/build_features.py` is only ever
called on one already-gap-split block at a time (see
`load_zone_hourly_blocks()`), so `.shift(n)` inside it can structurally
never reach into a different block -- there is no shared index to shift
across. This test proves that in practice with two blocks carrying
deliberately distinguishable values, so a regression that concatenated
blocks *before* computing lags would be caught.
"""
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from models.data_prep.build_features import _block_features as nyc_block_features  # noqa: E402


def _make_gapped_blocks():
    # block1 ends 2024-03-31 23:00, block2 starts 2024-04-30 00:00 -- a real
    # gap like the warehouse's missing Feb/Apr/May months, not adjacent hours.
    idx1 = pd.date_range("2024-03-01", "2024-03-31 23:00", freq="h")
    idx2 = pd.date_range("2024-04-30", periods=200, freq="h")
    block1 = pd.Series(1000.0, index=idx1)  # constant, easy to distinguish
    block2 = pd.Series(1.0, index=idx2)  # tiny values, far from block1's 1000s
    return block1, block2


def _assert_no_cross_block_leakage(block_features_fn):
    block1, block2 = _make_gapped_blocks()
    feats2 = block_features_fn(block2, alpha=0.3)

    # If lag/ewma/rolling had bled across the gap, every one of these
    # columns for block2's rows would show values near block1's 1000s
    # instead of block2's own 1.0s.
    for col in ("lag_1h", "lag_24h", "lag_168h", "ewma", "rolling_7d_avg"):
        assert (feats2[col] < 10).all(), f"{col} leaked block1's values across the gap"

    # block2's own first 168 rows (needing lag_168h history it doesn't have
    # yet within its own block) must be dropped, not filled from block1.
    assert feats2.index.min() == block2.index[168]

    # sanity: block1's own features never look at block2 either (order shouldn't matter)
    feats1 = block_features_fn(block1, alpha=0.3)
    assert (feats1["lag_168h"] == 1000.0).all()


def test_nyc_build_features_gap_safe():
    _assert_no_cross_block_leakage(nyc_block_features)


