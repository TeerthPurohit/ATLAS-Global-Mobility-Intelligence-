#!/bin/bash
# Deploy script run ON the backend EC2 instance (ADR-014), via SSM
# RunShellScript triggered by .github/workflows/deploy-backend-aws.yml.
#
# __ECR_REPO_URI__/__IMAGE_TAG__/__AWS_REGION__ are baked in by the workflow
# via `sed` before this is base64-encoded and sent (same templating
# convention scripts/aws_dbt_build_userdata.sh already uses -- SSM commands
# have no first-class templating either). COMPOSE_B64/CADDY_B64 are prepended
# as shell variable assignments by the workflow, ahead of this script's own
# content, before the whole thing is base64-encoded for transport.
set -euo pipefail

echo "[deploy] writing docker-compose.yml + Caddyfile"
mkdir -p /opt/app
echo "$COMPOSE_B64" | base64 -d > /opt/app/docker-compose.yml
echo "$CADDY_B64" | base64 -d > /opt/app/Caddyfile

ECR_REPO_URI="__ECR_REPO_URI__"
REGISTRY="${ECR_REPO_URI%%/*}"

echo "[deploy] logging in to ECR (${REGISTRY})"
aws ecr get-login-password --region __AWS_REGION__ | docker login --username AWS --password-stdin "${REGISTRY}"

cd /opt/app
export ECR_REPO_URI="__ECR_REPO_URI__"
export IMAGE_TAG="__IMAGE_TAG__"

echo "[deploy] pulling ${ECR_REPO_URI}:${IMAGE_TAG}"
docker compose pull

echo "[deploy] starting stack"
docker compose up -d

echo "[deploy] pruning old images"
docker image prune -f >/dev/null || true

echo "[deploy] done"
