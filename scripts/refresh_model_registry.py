"""Phase 4: regenerate `dbt_project/seeds/model_registry.csv`'s
`training_period` column from each row's own `metrics_ref` metadata JSON,
so an uncommitted retrain (e.g. NYC XGBoost's `xgb_metadata.json`) never
leaves the registry describing a stale date range.

Preserves the existing CSV schema and every other column (model_id,
city_id, artifact_path, status, ...) exactly -- those aren't derivable from
metadata JSON alone (it doesn't carry model_id/status for most models), so
this script refreshes dates, not registration. Rows whose `metrics_ref`
isn't a metadata JSON with a `date_range` (e.g. the rule-based journey
predictor, pointed at an ADR doc) are left untouched.

`training_period` format: train-start/val-start/test-start month, matching
the registry's existing "YYYY-MM/YYYY-MM/YYYY-MM" convention, deduped if
two splits start in the same month.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_CSV = REPO_ROOT / "dbt_project" / "seeds" / "model_registry.csv"


def _training_period_from_metadata(meta_path: Path) -> str | None:
    if not meta_path.exists() or meta_path.suffix != ".json":
        return None
    try:
        meta = json.loads(meta_path.read_text())
    except json.JSONDecodeError:
        return None
    date_range = meta.get("date_range")
    if not date_range:
        return None
    months = []
    for split in ("train", "val", "test"):
        start = date_range.get(split, [None])[0]
        if start:
            month = start[:7]  # "YYYY-MM-DD..." -> "YYYY-MM"
            if not months or months[-1] != month:
                months.append(month)
    return "/".join(months) if months else None


def refresh(csv_path: Path = REGISTRY_CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path, keep_default_na=False)  # "n/a" is a literal value here, not a null
    for i, row in df.iterrows():
        meta_path = REPO_ROOT / row["metrics_ref"]
        period = _training_period_from_metadata(meta_path)
        if period is not None:
            df.at[i, "training_period"] = period
    df.to_csv(csv_path, index=False)

    registered = {REPO_ROOT / p for p in df["metrics_ref"]}
    unregistered = [
        p for p in (REPO_ROOT / "models").glob("*/*_metadata.json") if p not in registered
    ]
    if unregistered:
        print("metadata files not referenced by any registry row (not added -- no model_id/status to infer):")
        for p in unregistered:
            print(f"  {p.relative_to(REPO_ROOT)}")
    return df


def demo() -> None:
    """Self-check on a throwaway copy: a metadata file with a later
    date_range must change training_period; a missing/malformed metrics_ref
    must leave the row untouched."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        meta_dir = tmp / "models" / "fake_model"
        meta_dir.mkdir(parents=True)
        meta_path = meta_dir / "fake_metadata.json"
        meta_path.write_text(json.dumps({"date_range": {
            "train": ["2025-01-01", "2025-01-31"],
            "val": ["2025-02-01", "2025-02-15"],
            "test": ["2025-03-01", "2025-03-31"],
        }}))
        csv_path = tmp / "model_registry.csv"
        csv_path.write_text(
            "model_id,city_id,metric,model_type,version,artifact_path,training_period,status,metrics_ref\n"
            "fake_v1,nyc,demand,xgboost,v1,x,STALE,active,models/fake_model/fake_metadata.json\n"
            "no_meta_v1,nyc,journey,rule_based,v1,x,2024-01,active,docs/some.md\n"
        )
        global REPO_ROOT
        old_root = REPO_ROOT
        REPO_ROOT = tmp
        try:
            df = refresh(csv_path)
        finally:
            REPO_ROOT = old_root
        assert df.loc[df["model_id"] == "fake_v1", "training_period"].iloc[0] == "2025-01/2025-02/2025-03"
        assert df.loc[df["model_id"] == "no_meta_v1", "training_period"].iloc[0] == "2024-01"
    print("refresh_model_registry demo OK")


if __name__ == "__main__":
    demo()
    refresh()
    print(f"refreshed {REGISTRY_CSV}")
