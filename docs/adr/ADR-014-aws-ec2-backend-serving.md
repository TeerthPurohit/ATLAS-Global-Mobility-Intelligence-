# ADR-014: AWS EC2 (not ECS/Fargate, not Oracle) for backend serving

**Status:** Accepted

## Context

The backend needed a real host. Two things were true going in:

- The project already runs a permanently-free Oracle Always-Free VM
  (`infra/local-model-vm/`, 2 OCPU/12GB shared tenancy budget) serving the
  fine-tuned QueryPlan model, and `docker-compose.oracle.yml` already runs
  the full backend stack there too — the cheapest possible option was
  already partially built.
- The user explicitly chose AWS anyway, for its resume value, having
  weighed that against the cost difference. That is a deliberate,
  acknowledged tradeoff, not an oversight — recorded here so a future
  session doesn't "optimize" it back to Oracle without re-raising the
  resume-value reason it was rejected.

Given AWS, the remaining choice was compute shape: ECS Fargate + ALB
(container orchestration, the more resume-recognizable "cloud-native"
combination) vs. a single EC2 instance running the same Docker Compose +
Caddy shape the Oracle VM already uses.

## Decision

**EC2, single `t4g.small` (Graviton/ARM64) instance**, Docker Compose +
Caddy for TLS — see `infra/cdk/backend_stack.py`.

Not ECS Fargate + ALB: that combination costs roughly 3x as much per month
for this deployment (ALB's fixed hourly fee dominates) while providing
autoscaling that isn't used — this is one task, no autoscaling policy,
because the current traffic doesn't need one. Fargate's actual selling
point isn't in play here, so its premium buys nothing. If real multi-region
or elastic-scaling needs ever show up, that's a new ADR, not a default.

Key design choices:

- **No self-hosted OSRM or Qdrant on the instance.**
  `backend/adapters/routing_osrm.py` already defaults `OSRM_URL` to OSRM's
  own public demo server with a haversine fallback if it's unavailable —
  identical behavior to what the default (non-oracle) `docker-compose.yml`
  already gets by never setting `OSRM_BASE_URL`. Qdrant Cloud's free tier
  is the user's actual target vector store, not a local container. Skipping
  both keeps `docker-compose.aws.yml` to just `caddy` + `backend`, which
  matters on a 2GB instance (`docker-compose.oracle.yml`'s self-hosted
  `osrm-routed` process holds an in-memory NYC road network it doesn't need
  to on AWS).
- **No NAT gateway.** The instance sits in the default VPC's public subnet
  with its own Elastic IP and reaches Neon/Qdrant Cloud/ECR over the
  Internet Gateway directly — a NAT gateway is only needed for private-
  subnet egress, and its ~$32/mo fixed cost would roughly double this
  stack's bill for a single stateless instance with no reason to hide its
  IP. Same reasoning `NycTlcDbtBuildStack` (ADR-009) already used.
- **No SSH key pair.** The instance role gets `AmazonSSMManagedInstanceCore`
  for AWS Systems Manager Session Manager; port 22 is never opened. Only
  80/443 (Caddy) are inbound.
- **OIDC federation, not access keys**, reusing the same GitHub OIDC
  provider `NycTlcDbtBuildStack` already creates (AWS allows one per
  account) — `infra/cdk/app.py` passes `existing_oidc_provider_arn` to both
  stacks.
- **Manual `cdk deploy`, manual DuckDB artifact rebuild, manual `.env`
  placement.** All three match existing, already-documented policy:
  `NycTlcDbtBuildStack`'s own "deploy from a developer machine, never CI"
  stance (ADR-009), ADR-005's "manual redeploy step, not automatic" for
  `scripts/build_deployed_duckdb.py`, and `Infrastructure.md`'s explicit
  out-of-scope listing for "secrets manager beyond `.env`." None of these
  are new gaps introduced by this ADR.
- **`.github/workflows/deploy-backend-aws.yml` is `workflow_dispatch`
  only**, not triggered on push to `main` — same manual-redeploy reasoning,
  and consistent with `dbt-build-aws.yml`'s own trigger.

## Why

A single EC2 instance running the same Compose+Caddy shape already proven
on the Oracle VM is the smallest AWS footprint that (a) satisfies the
explicit resume-value requirement for using AWS at all, and (b) doesn't add
orchestration machinery (ALB, ECS control plane, autoscaling policy) this
project has no current need for (rule 7). It is a genuinely more expensive
choice than staying on Oracle — that tradeoff was made deliberately by the
user, not discovered as a cost optimization.

## Consequences

- Real, recurring AWS cost (~EC2 `t4g.small` on-demand pricing, roughly
  $12-15/mo at time of writing — not yet measured against an actual bill;
  treat as an estimate, not a fabricated exact figure) that Oracle hosting
  would not have incurred. Acceptable per the explicit resume-value
  decision above.
- `docker-compose.oracle.yml` is unchanged and keeps serving the QueryPlan
  model on Oracle — this ADR adds a second, independent deployment target
  for the backend, it does not retire the first.
- Sizing (`t4g.small`, 2GB RAM) is a starting point, not a measured
  guarantee — `docker stats` against the real backend+Caddy footprint
  (post OSRM/Qdrant removal) should be checked before or shortly after the
  first real deploy; bumping to `t4g.medium` in
  `infra/cdk/backend_stack.py`'s `SERVE_INSTANCE_TYPE` is a one-line change
  if it doesn't fit.
- If ECS/Fargate autoscaling is ever genuinely needed (real concurrent
  traffic the single instance can't absorb), that's a new ADR superseding
  this one's compute-shape decision — not a silent rewrite of
  `backend_stack.py`.
