#!/bin/bash
# EC2 user-data for the on-demand dbt-build instance (ADR-009).
#
# Runs once at boot on a fresh Amazon Linux 2023 instance launched by
# .github/workflows/dbt-build-aws.yml, then self-terminates -- success or
# failure. Nothing here is meant to be re-run manually; if you need to
# debug a failure, read the CloudWatch/console log the instance leaves
# behind before it terminates (or temporarily comment out the `shutdown`
# call while iterating).
#
# What this does NOT do (rule 8, precompute for deployment): it doesn't
# retrain models, rebuild the RAG index, or touch anything the live backend
# reads at request time -- it only rebuilds the DuckDB warehouse (staging/
# intermediate/marts) that `dbt build` produces from raw parquet. dbt SQL
# itself is untouched; see dbt_project/models/.
set -euo pipefail

# S3_BUCKET is baked in by the workflow via `sed` before the instance is
# launched (EC2 user-data has no first-class templating). Everything else
# below is a fixed path convention, not per-run config.
S3_BUCKET="__S3_BUCKET__"
REPO_URL="https://github.com/__GITHUB_REPO__.git"
REPO_DIR="/opt/nyc-tlc-build"
WAREHOUSE_PREFIX="s3://${S3_BUCKET}/warehouse"
RAW_PREFIX="s3://${S3_BUCKET}/raw"

# Whatever happens -- success, a failed step, or a bug in this script --
# self-terminate. InstanceInitiatedShutdownBehavior=terminate (set at launch
# by the workflow) turns this shutdown into a full terminate, not a stop, so
# there is zero idle cost either way. On a non-zero exit, also drop a
# _FAILURE marker so the workflow's poll loop can report failure fast
# instead of waiting out the full timeout.
on_exit() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "[build] failed with exit code ${status}, writing failure marker"
        echo "exit ${status}" | aws s3 cp - "${WAREHOUSE_PREFIX}/_FAILURE" || true
    fi
    shutdown -h now
}
trap on_exit EXIT

echo "[build] installing system deps"
dnf install -y git python3.11 python3.11-pip awscli >/dev/null

echo "[build] cloning ${REPO_URL}"
git clone --depth 1 "${REPO_URL}" "${REPO_DIR}"
cd "${REPO_DIR}"

echo "[build] installing Python deps"
python3.11 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt

echo "[build] syncing raw NYC parquet + zone lookup from ${RAW_PREFIX}"
mkdir -p data/raw data/lookup data/warehouse
aws s3 sync "${RAW_PREFIX}/nyc/" data/raw/ --only-show-errors
aws s3 sync "${RAW_PREFIX}/lookup/" data/lookup/ --only-show-errors

echo "[build] loading raw parquet into DuckDB"
python scripts/load_raw_to_duckdb.py

echo "[build] loading London Santander Cycle Hire data (self-downloading, no S3 sync needed)"
python scripts/ingest_tfl_cycle_hire.py

echo "[build] dbt seed + build"
export DBT_PROFILES_DIR="${REPO_DIR}/dbt_project"
export DBT_PROJECT_DIR="${REPO_DIR}/dbt_project"
cd dbt_project
dbt seed
dbt build
cd ..

echo "[build] uploading finished warehouse artifacts to ${WAREHOUSE_PREFIX}"
aws s3 cp data/warehouse/nyc_rides.duckdb "${WAREHOUSE_PREFIX}/nyc_rides.duckdb"
aws s3 cp data/warehouse/london_cycles.duckdb "${WAREHOUSE_PREFIX}/london_cycles.duckdb"
# manifest.json/run_results.json feed backend/services/platform_service.py's
# pipeline-status widget -- small JSON, cheap to ship alongside the DuckDB
# files rather than making the deploy step regenerate them separately.
aws s3 cp dbt_project/target/manifest.json "${WAREHOUSE_PREFIX}/dbt/manifest.json"
aws s3 cp dbt_project/target/run_results.json "${WAREHOUSE_PREFIX}/dbt/run_results.json"

echo "[build] writing success marker"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | aws s3 cp - "${WAREHOUSE_PREFIX}/_SUCCESS"

echo "[build] done"
