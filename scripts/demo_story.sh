#!/usr/bin/env bash
set -euo pipefail
# Seed a synthetic alert (example: push a metric or call an attack)
curl -s -X POST http://localhost:8070/actions >/dev/null || true
# In a real demo, call attack_driver then rca_ai then run-script