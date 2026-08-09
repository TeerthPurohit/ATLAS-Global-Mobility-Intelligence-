"""The 522 TRANSFER-tier cities in `global_cities` must never become
training labels for the global transfer model -- only nyc/london (the 2
OBSERVED cities) may appear as rows in the joint training dataset. TRANSFER
cities are inference-time covariates only (task requirement)."""

import sys
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from models.global_transfer.train_global import NYC_DB, LONDON_DB, build_joint_dataset  # noqa: E402
from models.global_transfer.build_features import build_city_feature_table  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (NYC_DB.exists() and LONDON_DB.exists()), reason="warehouse not built"
)


def test_training_rows_only_observed_cities():
    df, _scaler = build_joint_dataset()
    assert set(df["city_id"].unique()) == {"nyc", "london"}


def test_transfer_cities_exist_but_are_excluded():
    con = duckdb.connect(str(NYC_DB), read_only=True)
    try:
        city_table = build_city_feature_table(con)
    finally:
        con.close()
    transfer_ids = set(city_table.loc[city_table["model_status"] == "TRANSFER", "city_id"])
    assert len(transfer_ids) > 0, "sanity: TRANSFER cities should actually exist in global_cities"

    df, _scaler = build_joint_dataset()
    assert not (set(df["city_id"].unique()) & transfer_ids), (
        "a TRANSFER city_id leaked into the training dataset as a labeled row"
    )
