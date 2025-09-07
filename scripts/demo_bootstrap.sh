#!/usr/bin/env bash
set -euo pipefail
# Bring base + observer + rca + hardening + tuner
docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up -d observer_hub rca_ai hardening_ai metrics_tuner attack_driver