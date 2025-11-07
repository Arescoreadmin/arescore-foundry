#!/usr/bin/env bash
set -euo pipefail

OPA_URL="${OPA_URL:-http://localhost:8181}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[training_gate_smoke] OPA_URL=${OPA_URL}"

check_bool () {
  local name="$1"
  local expected="$2"
  local actual="$3"

  if [[ "$actual" != "true" && "$actual" != "false" ]]; then
    echo "[training_gate_smoke] ${name}: expected boolean, got '${actual}'"
    exit 1
  fi

  if [[ "$actual" != "$expected" ]]; then
    echo "[training_gate_smoke] ${name}: expected ${expected}, got ${actual}"
    exit 1
  fi

  echo "[training_gate_smoke] ${name}: OK (${actual})"
}

echo "[training_gate_smoke] Checking OPA version..."
curl -s "${OPA_URL}/v1/data/system/version" | jq '.result.version' || {
  echo "[training_gate_smoke] Failed to get OPA version"
  exit 1
}

########################################
# GLOBAL training gate via policies/training_gate_test.rego
########################################
echo
echo "[training_gate_smoke] GLOBAL training gate tests"

GLOBAL_ALLOW_TRUE=$(
  curl -s "${OPA_URL}/v1/data/training_gate_test/test_training_gate_allows" \
    -H 'content-type: application/json' \
    -d '{}' | jq '.result'
)
check_bool "global_allow_true" "true" "${GLOBAL_ALLOW_TRUE}"

GLOBAL_ALLOW_FALSE=$(
  curl -s "${OPA_URL}/v1/data/training_gate_test/test_training_gate_denies_if_missing_fields" \
    -H 'content-type: application/json' \
    -d '{}' | jq '.result'
)
check_bool "global_allow_false" "true" "${GLOBAL_ALLOW_FALSE}"

########################################
# CONTAINER training gate via _container_policies/training_gate_test.rego
########################################
echo
echo "[training_gate_smoke] CONTAINER training gate tests"

CONTAINER_ALLOW_TRUE=$(
  curl -s "${OPA_URL}/v1/data/foundry/training/test_allow_true" \
    -H 'content-type: application/json' \
    -d '{}' | jq '.result'
)
check_bool "container_allow_true" "true" "${CONTAINER_ALLOW_TRUE}"

CONTAINER_ALLOW_FALSE=$(
  curl -s "${OPA_URL}/v1/data/foundry/training/test_allow_false_missing_label" \
    -H 'content-type: application/json' \
    -d '{}' | jq '.result'
)
check_bool "container_allow_false" "true" "${CONTAINER_ALLOW_FALSE}"

echo
echo "[training_gate_smoke] Done."
