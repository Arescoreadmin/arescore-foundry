#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
cd "$(dirname "$0")/.."

TARGET_DIR="_container_policies"
mkdir -p "${TARGET_DIR}"

echo "[ensure_container_policies] Ensuring ${TARGET_DIR} exists at $(pwd)/${TARGET_DIR}"

# 1) foundry.rego (container helpers)
FILE_FOUNDATION="${TARGET_DIR}/foundry.rego"
if [ -e "${FILE_FOUNDATION}" ]; then
  echo "[ensure_container_policies] ${FILE_FOUNDATION} already exists, leaving it alone."
else
  echo "[ensure_container_policies] Creating ${FILE_FOUNDATION}"
  cat > "${FILE_FOUNDATION}" << 'EOF'
package foundry

has_label(v) {
  some i
  input.metadata.labels[i] == v
}

net_denied {
  input.network.egress == "deny"
}

zero_exploits {
  input.limits.attacker_max_exploits == 0
}
EOF
fi

# 2) training_gate.rego (container training gate)
FILE_TG="${TARGET_DIR}/training_gate.rego"
if [ -e "${FILE_TG}" ]; then
  echo "[ensure_container_policies] ${FILE_TG} already exists, leaving it alone."
else
  echo "[ensure_container_policies] Creating ${FILE_TG}"
  cat > "${FILE_TG}" << 'EOF'
package foundry.training

default allow = false

allow {
  data.foundry.has_label("class:netplus")
  data.foundry.zero_exploits
  data.foundry.net_denied
}
EOF
fi

# 3) training_gate_test.rego (container tests)
FILE_TG_TEST="${TARGET_DIR}/training_gate_test.rego"
if [ -e "${FILE_TG_TEST}" ]; then
  echo "[ensure_container_policies] ${FILE_TG_TEST} already exists, leaving it alone."
else
  echo "[ensure_container_policies] Creating ${FILE_TG_TEST}"
  cat > "${FILE_TG_TEST}" << 'EOF'
package foundry.training

test_allow_true {
  data.foundry.training.allow with input as {
    "metadata": {"labels": ["class:netplus"]},
    "limits":   {"attacker_max_exploits": 0},
    "network":  {"egress": "deny"}
  }
}

test_allow_false_missing_label {
  not data.foundry.training.allow with input as {
    "metadata": {"labels": []},
    "limits":   {"attacker_max_exploits": 0},
    "network":  {"egress": "deny"}
  }
}
EOF
fi

echo "[ensure_container_policies] Done."
