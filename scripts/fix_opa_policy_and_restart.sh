cat > scripts/fix_opa_policy_and_restart.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo ">> Write fixed training_gate.rego"
install -d policies
cat > policies/training_gate.rego <<'REGO'
package foundry.training
default allow := false
allow {
  input.metadata.labels[_] == "class:netplus"
  input.limits.attacker_max_exploits == 0
  input.network.egress == "deny"
}
REGO

echo ">> Optional tests"
cat > policies/training_gate_test.rego <<'REGO'
package foundry.training
test_allow_true {
  allow with input as {
    "metadata": {"labels": ["class:netplus"]},
    "limits": {"attacker_max_exploits": 0},
    "network": {"egress": "deny"}
  }
}
test_allow_false_missing_label {
  not allow with input as {
    "metadata": {"labels": ["foo"]},
    "limits": {"attacker_max_exploits": 0},
    "network": {"egress": "deny"}
  }
}
REGO

echo ">> Local test via OPA container"
docker run --rm -v "$PWD/policies:/policies:ro" openpolicyagent/opa:0.67.0 test -v /policies

echo ">> Recreate OPA only"
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml up -d --force-recreate opa

echo ">> Probe OPA health"
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8181/health >/dev/null; then
    echo "OPA OK"
    exit 0
  fi
  sleep 1
done
echo "OPA health FAILED"; exit 1
SH
chmod +x scripts/fix_opa_policy_and_restart.sh
