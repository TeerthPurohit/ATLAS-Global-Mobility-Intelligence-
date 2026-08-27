"""Backward-compatible re-export.

The actual implementation moved to `chronological_split.py` (Phase 2 dedup,
IMPLEMENTATION_AUDIT.md section 9/10) so `models/fare_prediction/
train_fare_xgb.py` could drop its own duplicate copy of this logic and call
the shared functions directly. This module is kept so existing
`from data_prep.train_test_split import ...` / `from models.data_prep.
train_test_split import ...` call sites (ewma_baseline, linear_baseline,
xgboost_model, lstm_model, evaluation) keep working
unchanged.
"""

from __future__ import annotations

from .chronological_split import (
    _latest_month_start,  # noqa: F401
    chronological_split,  # noqa: F401
    demo,
    split_demand_blocks,  # noqa: F401
)

if __name__ == "__main__":
    demo()
