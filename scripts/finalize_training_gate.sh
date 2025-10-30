#!/usr/bin/env bash
set -euo pipefail

POL_DIR="policies"
GATE="${POL_DIR}/training_gate.rego"
FOUND="${POL_DIR}/foundry.rego"

[[ -d "$POL_DIR" ]] || { echo "missing $POL_DIR"; exit 2; }

echo "— Normalize gate rule name to 'gate_ok'…"
# Rename top-level 'allow {' in training_gate.rego to 'gate_ok {'
# (idempotent: only if rule head is exactly 'allow {')
if grep -qE '^[[:space:]]*allow[[:space:]]*{' "$GATE"; then
  sed -i.bak '0,/^[[:space:]]*allow[[:space:]]*{[[:space:]]*$/s//gate_ok {/' "$GATE"
fi

echo "— Ensure deny-by-default and binding allow := gate_ok in foundry.rego…"
cat > "$FOUND".tmp <<'REGO'
package foundry.training

default allow := false

# Gate binding: only pass when gate_ok holds
allow {
  gate_ok
}
REGO
mv "$FOUND".tmp "$FOUND"

echo "— Rename any OTHER 'allow {' in the same package to 'legacy_allow {' to kill implicit OR…"
# Find all rego files in package foundry.training except the two we manage
mapfile -t PKG_FILES < <(grep -RIl '^[[:space:]]*package[[:space:]]\+foundry\.training[[:space:]]*$' "$POL_DIR" | grep -v -E '(foundry\.rego|training_gate\.rego)')
for f in "${PKG_FILES[@]}"; do
  # Only touch exact rule head 'allow {' to avoid renaming symbols in comments/strings.
  if grep -qE '^[[:space:]]*allow[[:space:]]*{' "$f"; then
    sed -i.bak 's/^\([[:space:]]*\)allow[[:space:]]*{/\1legacy_allow {/' "$f"
  fi
done

echo "— Quick compile/test in OPA image…"
docker run --rm -v "$PWD/$POL_DIR:/policies:ro" openpolicyagent/opa:0.67.0 test -v /policies

echo "— Bounce OPA only and probe health…"
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml up -d --force-recreate opa
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8181/health >/dev/null; then echo "OPA OK"; break; fi
  sleep 1
done

echo "— Verify gate TRUE (class:netplus)…"
curl -s http://127.0.0.1:8181/v1/data/foundry/training/allow \
  -H 'content-type: application/json' -d @- <<'JSON'
{ "input": {
  "metadata": { "labels": ["class:netplus"] },
  "limits":   { "attacker_max_exploits": 0 },
  "network":  { "egress": "deny" }
} }
JSON

echo "— Verify gate FALSE (label foo)…"
curl -s http://127.0.0.1:8181/v1/data/foundry/training/allow \
  -H 'content-type: application/json' -d @- <<'JSON'
{ "input": {
  "metadata": { "labels": ["foo"] },
  "limits":   { "attacker_max_exploits": 0 },
  "network":  { "egress": "deny" }
} }
JSON

echo "— Git commit (optional)…"
git add "$FOUND" "$GATE" ${PKG_FILES[@]+"${PKG_FILES[@]}"}
git commit -m "OPA: single-source allow; gate_ok binding; kill implicit OR (rename other allow->legacy_allow)" || true
