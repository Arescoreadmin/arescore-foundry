#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE="infra/docker-compose.yml"
ORCH_DIR="services/orchestrator"
OPA_DIR="policies"
OPA_FILE="$OPA_DIR/foundry.rego"
DOCKERIGNORE="$ORCH_DIR/.dockerignore"

note(){ printf "==> %s\n" "$*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }

[[ -f "$COMPOSE" ]] || die "missing $COMPOSE"
[[ -d "$ORCH_DIR" ]] || die "missing $ORCH_DIR"

# 0) backup compose
cp -v "$COMPOSE" "${COMPOSE}.bak.$(date +%s)"

##############
# (1) depends_on: opa (healthy) under orchestrator
##############
note "Ensuring orchestrator depends_on -> opa (healthy)"

# quick check: already present?
if docker compose -f "$COMPOSE" config | sed -n '/^  orchestrator:/,/^  [^ ]/p' \
   | sed -n '/depends_on:/,/^[^ ]/p' | grep -qE '^\s+opa:\s*$'; then
  note "depends_on.opa already present — skipping insert"
else
  # If a depends_on block exists, append opa; else create a new depends_on block after container_name (or after build:)
  awk -v MODE="insert-opa" '
    BEGIN{in_orch=0; inserted=0; have_dep=0}
    /^  orchestrator:/{in_orch=1}
    in_orch && /^  [^ ]/{in_orch=0}
    { line=$0 }
    in_orch && /^\s+depends_on:/{have_dep=1}
    # Append opa under existing depends_on (only once)
    in_orch && have_dep && !inserted && /^\s+depends_on:\s*$/ {
      print line;
      print "      opa:";
      print "        condition: service_healthy";
      print "        required: true";
      inserted=1; next
    }
    # If no depends_on existed by the time we leave container_name/build, insert after first suitable anchor
    in_orch && !have_dep && !inserted && /^\s+(container_name|build):/ && anchor=="" { anchor=$1 }
    in_orch && !have_dep && !inserted && anchor!="" && $0!~/^\s+(container_name|build):/ && $0!~/^\s+dockerfile:/ {
      print "    depends_on:";
      print "      opa:";
      print "        condition: service_healthy";
      print "        required: true";
      inserted=1;
    }
    { print line }
  ' "$COMPOSE" > /tmp/compose.tmp && mv /tmp/compose.tmp "$COMPOSE"
fi

##############
# (2) Minimal OPA policy so health/eval endpoint exists
##############
note "Ensuring minimal OPA policy exists"
mkdir -p "$OPA_DIR"
if [[ ! -f "$OPA_FILE" ]]; then
  cat > "$OPA_FILE" <<'REGO'
package foundry.training
default allow = true
REGO
  note "Wrote $OPA_FILE"
else
  note "$OPA_FILE already present — leaving as-is"
fi

##############
# (3) .dockerignore for orchestrator
##############
note "Ensuring orchestrator/.dockerignore"
mkdir -p "$ORCH_DIR"
touch "$DOCKERIGNORE"
for pat in '__pycache__/' '*.pyc' '.env' '.git' '.gitignore' '.DS_Store'; do
  grep -qxF "$pat" "$DOCKERIGNORE" || echo "$pat" >> "$DOCKERIGNORE"
done

##############
# (4) Disable Uvicorn access logs via env
##############
note "Setting UVICORN_ACCESS_LOG=false in orchestrator env"
if docker compose -f "$COMPOSE" config | sed -n '/^  orchestrator:/,/^  [^ ]/p' \
   | sed -n '/environment:/,/^[^ ]/p' | grep -q 'UVICORN_ACCESS_LOG'; then
  note "UVICORN_ACCESS_LOG already present — skipping insert"
else
  awk '
    BEGIN{in_orch=0; in_env=0; inserted=0}
    /^  orchestrator:/{in_orch=1}
    in_orch && /^  [^ ]/{in_orch=0; in_env=0}
    {
      if(in_orch && /^    environment:\s*$/ && !inserted){
        print $0
        print "      UVICORN_ACCESS_LOG: \"false\""
        inserted=1; next
      }
      # If no environment block exists, create one after image/build/env anchors
      if(in_orch && !inserted && (/^\s+ports:$/ || /^\s+healthcheck:$/ || /^\s+networks:$/)){
        print "    environment:"
        print "      UVICORN_ACCESS_LOG: \"false\""
        inserted=1
      }
      print $0
    }
  ' "$COMPOSE" > /tmp/compose.tmp && mv /tmp/compose.tmp "$COMPOSE"
fi

echo
note "Validating compose after edits"
docker compose -f "$COMPOSE" config >/dev/null && echo "✅ compose OK"

cat <<'NEXT'
----------------------------------------------------------------
Next steps:
  docker compose -f infra/docker-compose.yml up -d opa --force-recreate
  docker compose -f infra/docker-compose.yml up -d orchestrator --force-recreate --no-deps
  curl -fsS http://127.0.0.1:8181/ && echo "OPA OK"
  curl -fsS http://127.0.0.1:8080/health && echo "orchestrator OK"
----------------------------------------------------------------
NEXT
