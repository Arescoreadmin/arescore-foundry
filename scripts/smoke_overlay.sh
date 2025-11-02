#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

echo "==> OPA unit tests"
docker run --rm -v "$PWD/policies":/policies:ro openpolicyagent/opa:1.10.0 test /policies -v >/dev/null
echo "OK: OPA tests passed"

echo "==> Ensuring stack is up (compose + federated)"
docker compose -f compose.yml -f compose.federated.yml up -d >/dev/null

fail=0
check() {
  local name="$1" url="$2" method="${3:-GET}"
  if curl -fsS -X "$method" "$url" >/dev/null; then
    echo "OK: $name"
  else
    echo "FAIL: $name ($method $url)" >&2
    fail=1
  fi
}

echo "==> Service health checks"
check fl_coordinator      "http://127.0.0.1:9092/health"
check consent_opt_in      "http://127.0.0.1:9093/consent/training/optin" POST
check consent_crl         "http://127.0.0.1:9093/crl"
check evidence_bundler    "http://127.0.0.1:9094/health"
check orchestrator        "http://127.0.0.1:8080/health"

if [[ "$fail" -ne 0 ]]; then
  echo "One or more checks failed." >&2
  exit 1
fi
echo "All green."
