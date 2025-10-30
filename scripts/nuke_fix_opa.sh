# scripts/nuke_fix_opa.sh
#!/usr/bin/env bash
set -euo pipefail

MAIN=${MAIN:-infra/docker-compose.yml}
OVR=${OVR:-infra/compose.opa.yml}
SERVICE=${SERVICE:-opa}
PIN=${PIN:-1}    # set PIN=0 to skip digest pinning
RESTART=${RESTART:-1}

mkdir -p infra policies
cp -v "$OVR" "$OVR.bak.$(date +%s)" 2>/dev/null || true

# 1) Write a clean, hardened OPA override (no junk at line 71 ever again)
cat > "$OVR" <<'YML'
services:
  opa:
    image: openpolicyagent/opa:0.67.0
    command: ["run","--server","--log-level=info","/policies"]
    volumes:
      - ../policies:/policies:ro
    ports:
      - "8181:8181"
    read_only: true
    cap_drop: ["ALL"]
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
    healthcheck:
      test: ["CMD","wget","-qO-","http://127.0.0.1:8181/health"]
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 15s
YML

# minimal policy so /health serves instantly
cat > policies/foundry.rego <<'REGO'
package foundry.training
default allow = true
REGO

# 2) Validate compose. If this fails, show the offending lines with context.
if ! docker compose -f "$MAIN" -f "$OVR" config >/dev/null 2> >(tee /tmp/compose_err.log >&2); then
  echo "❌ compose parse failed — showing neighborhood:" >&2
  if grep -Eo 'line ([0-9]+)' /tmp/compose_err.log >/dev/null; then
    L=$(grep -Eo 'line ([0-9]+)' /tmp/compose_err.log | awk '{print $2}' | tail -1)
    nl -ba "$OVR" | sed -n "$((L-10)),$((L+10))p" >&2 || true
  fi
  exit 1
fi
echo "✅ override repaired & valid"

# 3) (Optional) pin OPA by digest
if [[ "$PIN" == "1" ]]; then
  # extract tag from the file (default to 0.67.0)
  TAG=$(awk '/^\s*image:\s*openpolicyagent\/opa:/{sub(/.*:/,""); print; exit}' "$OVR")
  TAG=${TAG:-0.67.0}
  echo ">> Pulling openpolicyagent/opa:${TAG}…"
  docker pull "openpolicyagent/opa:${TAG}" >/dev/null
  DIGEST=$(docker inspect --format '{{index .RepoDigests 0}}' "openpolicyagent/opa:${TAG}" | sed -E 's/.*@//')
  [[ $DIGEST =~ ^sha256:[a-f0-9]{64}$ ]] || { echo "❌ bad digest"; exit 1; }
  echo ">> Pinning digest: $DIGEST"
  # replace image line with tag@digest
  sed -E -i "s#(^\s*image:\s*openpolicyagent/opa:)[A-Za-z0-9_.-]+(\s*)\$#\1${TAG}@${DIGEST}\2#" "$OVR"
  docker compose -f "$MAIN" -f "$OVR" config >/dev/null
  echo "✅ pinned and valid"
else
  echo ">> Skipping digest pin (PIN=0)"
fi

# 4) Recreate OPA (and orchestrator for depends_on checks), probe health
if [[ "$RESTART" == "1" ]]; then
  docker compose -f "$MAIN" -f "$OVR" up -d --force-recreate "$SERVICE" orchestrator
  # backoff health probes
  for i in {1..60}; do
    curl -fsS http://127.0.0.1:8181/health >/dev/null 2>&1 && { echo "✅ OPA healthy"; break; }
    sleep 1
    [[ $i -eq 60 ]] && { echo "⚠️ OPA not healthy; logs tail:"; docker compose -f "$MAIN" -f "$OVR" logs --no-log-prefix "$SERVICE" | tail -200; exit 1; }
  done
  curl -fsS http://127.0.0.1:8080/health >/dev/null && echo "✅ Orchestrator healthy"
else
  echo ">> Skipping restart (RESTART=1 to enable)"
fi

echo "— Done"
