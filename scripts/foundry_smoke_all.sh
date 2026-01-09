#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[foundry_smoke_all] Using python: $(which python || true)"
echo "[foundry_smoke_all] Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
echo

########################################
# 1. frostgatecore tests (lightweight)
########################################
echo "[foundry_smoke_all] Step 1/4: backend/frostgatecore pytest (API only)"
(
  cd backend/frostgatecore
  pytest Tests/test_api.py
)
echo "[foundry_smoke_all] frostgatecore basic API tests OK"
echo

########################################
# 2. OPA + policies
########################################
echo "[foundry_smoke_all] Step 2/4: OPA up + policy_smoke"
./scripts/opa_up.sh
./scripts/policy_smoke.sh
echo "[foundry_smoke_all] OPA/policies OK"
echo

########################################
# 3. Foundry flow
########################################
echo "[foundry_smoke_all] Step 3/4: Foundry flow smoke"
./scripts/foundry_flow_smoke.sh
echo "[foundry_smoke_all] Foundry flow OK"
echo

########################################
# 4. Training gate specific smoke (OPA-level)
########################################
echo "[foundry_smoke_all] Step 4/4: Training gate smoke (OPA direct)"
./scripts/training_gate_smoke.sh
echo "[foundry_smoke_all] Training gate OK"
echo

echo "[foundry_smoke_all] ALL SMOKES PASSED."
