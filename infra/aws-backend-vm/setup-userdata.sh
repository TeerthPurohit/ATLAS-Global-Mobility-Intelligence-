#!/usr/bin/env bash
# infra/aws-backend-vm/setup-userdata.sh -- EC2 user-data for the backend
# serving instance (infra/cdk/backend_stack.py, Amazon Linux 2023 arm64/
# t4g.small). Runs once at first boot: installs Docker + the Compose
# plugin, creates /opt/app, and installs a systemd unit so
# `docker compose up -d` re-runs after every reboot (the containers
# themselves use `restart: unless-stopped` for in-place crash recovery --
# this unit only covers a full instance reboot, matching the
# reboot-durability already verified for infra/local-model-vm).
#
# The actual docker-compose.yml/Caddyfile/.env content is written by
# .github/workflows/deploy-backend-aws.yml on each deploy, not here -- user
# data only runs once, at instance creation, so anything that needs to
# change on redeploy can't live in it.
set -euo pipefail

dnf install -y docker
systemctl enable --now docker

mkdir -p /usr/libexec/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" \
    -o /usr/libexec/docker/cli-plugins/docker-compose
chmod +x /usr/libexec/docker/cli-plugins/docker-compose

mkdir -p /opt/app/certs
touch /opt/app/.env
chmod 600 /opt/app/.env

cat > /etc/systemd/system/app-compose.service <<'UNIT_EOF'
[Unit]
Description=Backend docker compose stack
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/app
ExecStart=/usr/bin/docker compose -f /opt/app/docker-compose.yml up -d
ExecStop=/usr/bin/docker compose -f /opt/app/docker-compose.yml down

[Install]
WantedBy=multi-user.target
UNIT_EOF

systemctl daemon-reload
systemctl enable app-compose.service
# Not started here -- /opt/app/docker-compose.yml doesn't exist until the
# first deploy workflow run writes it.
