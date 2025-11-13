#!/usr/bin/env bash
set -euo pipefail

echo "[rollup] building overlay + voice services"
docker compose -f compose.yml -f compose.rollup.yml --profile control-plane build network_overlay voice_gateway
