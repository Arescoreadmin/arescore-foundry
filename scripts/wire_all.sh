#!/usr/bin/env bash
set -Eeuo pipefail

echo "==> 1) Ensure readiness probe"
scripts/wire_readyz.sh

echo "==> 2) Ensure metrics are exposed"
if [ -f scripts/enable_metrics_orchestrator.sh ]; then
  scripts/enable_metrics_orchestrator.sh || true
fi

echo "==> 3) Enable gzip_static + precompression"
scripts/enable_gzip_static.sh

echo "==> 4) Quick smoke"
set +e
curl -fsS http://127.0.0.1:8000/health >/dev/null && echo " /health OK"
curl -fsS http://127.0.0.1:8000/_healthz >/dev/null && echo " /_healthz OK" || echo " /_healthz (optional) missing"
curl -fsS http://127.0.0.1:8000/readyz >/dev/null && echo " /readyz OK"
curl -fsS http://127.0.0.1:8000/metrics >/dev/null && echo " /metrics OK (if instrumented)" || echo " /metrics not present (ok if not enabled)"
set -e

echo "==> Done."
