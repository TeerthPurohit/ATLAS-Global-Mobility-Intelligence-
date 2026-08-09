"""Phase 4: refresh_model_registry.py must update training_period from real
metadata and must never turn the literal string "n/a" into an empty cell
(pandas' default NA-sniffing on read_csv would do exactly that)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import refresh_model_registry as m  # noqa: E402
from refresh_model_registry import demo  # noqa: E402


def test_refresh_demo_self_check():
    demo()


def test_registry_preserves_na_literal_and_updates_stale_period():
    repo_root = Path(__file__).resolve().parents[1]
    df = m.refresh(repo_root / "dbt_project" / "seeds" / "model_registry.csv")
    row = df[df["model_id"] == "journey_predictors_v1"].iloc[0]
    assert row["training_period"] == "n/a"

    nyc = df[df["model_id"] == "xgboost_demand_v1"].iloc[0]
    import json

    meta = json.loads((repo_root / "models" / "xgboost_model" / "xgb_metadata.json").read_text())
    expected_start = meta["date_range"]["train"][0][:7]
    assert nyc["training_period"].startswith(expected_start)


if __name__ == "__main__":
    test_refresh_demo_self_check()
    test_registry_preserves_na_literal_and_updates_stale_period()
    print("test_refresh_model_registry OK")
