# ADR-009: On-demand AWS EC2 for `dbt build`, triggered from GitHub Actions

**Status:** Accepted

## Context

`dbt build` now materializes `int_trips_enriched` (113M+ HVFHV rows) plus
every downstream mart. The local dev machine has ~2GB free RAM out of 16GB
and ~41GB free disk out of 476GB — a full local build competes with
everything else running on the machine and risks OOM/disk-exhaustion
failures partway through a run that takes real wall-clock time to redo.

This is a build-time problem only. It does not touch the deployed backend
(which already reads a precomputed, read-only DuckDB file per
`docs/architecture/Infrastructure.md`) or the dbt SQL itself
(`dbt_project/models/{staging,intermediate,marts}` are unchanged — same
DuckDB engine, same layering, see ADR-001 and ADR-002).

## Decision

Move the `dbt build` *execution* to an on-demand AWS EC2 instance, launched
by a GitHub Actions `workflow_dispatch` job and torn down automatically when
the build finishes (success or failure). Infra is defined as code in
`infra/cdk/` (AWS CDK, Python) — S3 for raw-parquet input and
finished-warehouse output, an IAM role for the EC2 instance, an IAM role for
GitHub Actions to assume via OIDC, and an outbound-only security group.
Nothing else (no RDS, no ECS/EKS, no VPC of our own — see Consequences).

Key design choices, in order of how much they cost if gotten wrong:

- **OIDC federation, not access keys.** GitHub Actions assumes
  `GitHubActionsBuildRole` via `token.actions.githubusercontent.com`, scoped
  to this repo's `main` branch (`sub: repo:{org}/{repo}:ref:refs/heads/main`).
  No AWS access key/secret is stored as a GitHub secret — nothing to leak,
  nothing to rotate.
- **Self-terminating instance, on-demand only.** The EC2 instance is
  launched with `InstanceInitiatedShutdownBehavior=terminate`; the user-data
  script (`scripts/aws_dbt_build_userdata.sh`) runs `shutdown -h now` in an
  `EXIT` trap covering both success and failure. There is no idle-cost
  window — the instance exists only for the ~30-60 minutes a build takes.
  The GitHub Actions job also force-terminates it after a timeout as a
  safety net for a hang that never reaches the trap (e.g. a wedged process).
- **`r6i.xlarge` (4 vCPU / 32GB RAM), memory-optimized family.** The
  113M-row materialization is a memory-bound aggregation/join, not
  compute-bound — RAM headroom matters more than core count. This is a
  judgment call, not a benchmarked number (rule 2 — no fabricated metric
  here); it's sized to comfortably clear the 113M-row job based on DuckDB's
  documented rule of thumb (roughly working-set-size-dependent, not
  linear-in-row-count, but 32GB is a wide margin over the local machine's
  2GB free). If a real run shows it's oversized or undersized, resize the
  constant in `infra/cdk/stack.py` — don't add auto-scaling for a one-shot
  batch job.
- **No VPC of our own, no NAT gateway.** The instance launches into the
  account's existing default VPC/public subnet with a public IP and
  outbound-only security group (no inbound rules, no SSH key pair — nothing
  needs to reach it, it reaches S3 and pip/dnf mirrors). A NAT gateway would
  be an always-on hourly cost for something that only needs egress for 30-60
  minutes a few times total; the public-subnet + no-inbound-SG combination
  gets the same "nothing can reach in" property without it.
- **S3 as the only hand-off point.** Raw parquet goes into `raw/`
  (uploaded once, manually, by the developer — this ADR does not add an
  automated raw-data ingestion pipeline, that's a separate concern already
  covered by `scripts/load_raw_to_duckdb.py`'s local-file assumption). The
  finished `nyc_rides.duckdb` / `london_cycles.duckdb` and dbt's
  `manifest.json`/`run_results.json` land in `warehouse/`, along with a
  `_SUCCESS` (or `_FAILURE`) marker object that the GitHub Actions job polls
  for instead of trying to SSH in or tail logs live.
- **dbt source config is unchanged.** `dbt_project/models/staging/schema.yml`'s
  `source('nyc_tlc', 'raw_trips')` already resolves against the DuckDB
  database itself (`raw_trips` is a view created by
  `scripts/load_raw_to_duckdb.py` from local parquet), not a dbt-level S3
  source config — so the only change needed is *where the parquet lives
  before that script runs* (synced from S3 to the instance's local disk by
  the user-data script), not any dbt YAML.

## Why

An on-demand, self-terminating instance triggered manually is the smallest
infra that solves "the local machine can't hold this build" without adding
always-on cost or a always-on service to operate. A managed batch service
(AWS Batch, Step Functions) would add orchestration machinery for a single
job that runs a handful of times total — not worth it at this scale (rule
7). A always-on build server would cost money every hour it isn't building,
for a task that happens on demand, not continuously.

## Consequences

- Running a build costs real (small) money: EC2 on-demand `r6i.xlarge`
  plus S3 storage/transfer, for however long a build takes. Acceptable for
  a portfolio project's occasional rebuild; would need reconsidering if this
  became a frequent (e.g. daily) job — it is deliberately not scheduled
  (`.github/workflows/dbt-build-aws.yml` is `workflow_dispatch` only, no
  cron) for exactly that reason.
- `cdk deploy` must be run manually from a developer machine with real AWS
  credentials — CI never gets deploy/infra-provisioning permissions, only
  the narrow runtime permissions in `GitHubActionsBuildRole` (launch/poll/
  terminate one tagged instance type, read/write two S3 prefixes). This is
  intentional, not a gap: infra changes should go through a human running
  `cdk diff`/`cdk deploy` locally, not an unattended CI job with
  infrastructure-provisioning IAM permissions.
- The GitHub OIDC provider is a per-AWS-account singleton. If the target
  account already has one (e.g. from another project), `infra/cdk/app.py`
  accepts `-c existing_oidc_provider_arn=...` to import it instead of
  failing on a duplicate-resource error.
- This does not change ADR-001 (DuckDB stays the analytical engine) or
  ADR-002 (dbt layering) — it changes only *where* `dbt build` executes.
  The deployed backend still reads a slimmed, precomputed DuckDB file per
  `docs/architecture/Deployment.md`; copying the finished warehouse artifact
  from S3 into that slimmed deploy file is a manual step for now (same as
  before this ADR — deployment was already a documented-but-manual process,
  see `docs/architecture/Deployment.md`).
