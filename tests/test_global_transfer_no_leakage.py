"""Leakage-guard test for models/global_transfer/train_global.py (ADR-003,
rule 3): the joint NYC+London chronological split must never let a training
row's timestamp be >= a test row's timestamp."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from models.global_transfer.train_global import NYC_DB, LONDON_DB, build_joint_dataset  # noqa: E402
from models.data_prep.chronological_split import chronological_split  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (NYC_DB.exists() and LONDON_DB.exists()), reason="warehouse not built"
)


def test_global_transfer_chronological_split_no_leakage():
    df, _scaler = build_joint_dataset()
    train, val, test = chronological_split(df, "ts", (0.7, 0.15, 0.15))

    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["ts"].max() < val["ts"].min()
    assert val["ts"].max() < test["ts"].min()
