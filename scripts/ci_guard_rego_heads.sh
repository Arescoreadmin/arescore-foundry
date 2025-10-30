#!/usr/bin/env bash
set -euo pipefail
bad=$(grep -RIl '^[[:space:]]*package[[:space:]]\+foundry\.training[[:space:]]*$' policies \
  | grep -v 'foundry\.rego' \
  | xargs -r grep -n '^[[:space:]]*allow[[:space:]]*{' || true)
if [[ -n "$bad" ]]; then
  echo "ERROR: Found extra 'allow {' heads in foundry.training (must only exist in foundry.rego):"
  echo "$bad"; exit 1
fi
docker run --rm -v "$PWD/policies:/policies:ro" openpolicyagent/opa:0.67.0 test -v /policies
