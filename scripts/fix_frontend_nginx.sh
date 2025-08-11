#!/usr/bin/env bash
set -Eeuo pipefail

# --- config ---------------------------------------------------
FRONT_SVC="frontend"
BASE_COMPOSE="infra/docker-compose.yml"
HARDEN_OVERRIDE="infra/docker-compose.hardening.override.yml"   # optional
TMPFS_OVERRIDE="infra/docker-compose.frontend-tmpfs.override.yml"
FRONT_DIR="frontend"
DF="$FRONT_DIR/Dockerfile"
GZIP_CONF="$FRONT_DIR/nginx-gzip.conf"
# --------------------------------------------------------------

msg(){ echo -e "=> $*"; }
die(){ echo "❌ $*" >&2; exit 1; }

# Ensure we're at repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

[[ -f "$BASE_COMPOSE" ]] || die "Missing $BASE_COMPOSE"

# 1) Write a clean gzip config (omits text/html to avoid duplicate MIME warning)
msg "Writing optimized gzip config: $GZIP_CONF"
mkdir -p "$FRONT_DIR"
cat >"$GZIP_CONF" <<'CONF'
# Loaded in http {} via /etc/nginx/conf.d/*.conf
gzip on;
gzip_comp_level 5;
gzip_min_length 256;
gzip_proxied any;
gzip_vary on;
gzip_static on;
gzip_types
  text/plain
  text/css
  application/javascript
  application/json
  application/xml
  image/svg+xml;
CONF

# 2) Ensure Dockerfile copies the gzip conf into the runtime image
if [[ ! -f "$DF" ]]; then
  die "Dockerfile not found at $DF"
fi

if ! grep -q 'nginx-gzip.conf' "$DF"; then
  msg "Patching $DF to COPY nginx-gzip.conf into /etc/nginx/conf.d/gzip.conf"
  awk '
    { print }
    /COPY[[:space:]]+--from=builder/ && /\/usr\/share\/nginx\/html\/?/ && !patched {
      print "";
      print "# Enable gzip for text assets";
      print "COPY --chown=101:101 nginx-gzip.conf /etc/nginx/conf.d/gzip.conf";
      patched=1
    }
    END {
      if (!patched) {
        print "";
        print "# (Fallback) Enable gzip for text assets";
        print "COPY --chown=101:101 nginx-gzip.conf /etc/nginx/conf.d/gzip.conf";
      }
    }
  ' "$DF" > "$DF.tmp" && mv "$DF.tmp" "$DF"
else
  msg "Dockerfile already copies gzip conf — OK"
fi

# 3) Create a tmpfs override so nginx can write /tmp while container remains read-only
msg "Writing $TMPFS_OVERRIDE (tmpfs for /tmp)"
cat >"$TMPFS_OVERRIDE" <<YAML
services:
  ${FRONT_SVC}:
    tmpfs:
      - /tmp
YAML

# 4) Rebuild + restart frontend with overrides
msg "Rebuilding $FRONT_SVC…"
COMPOSE_ARGS=(-f "$BASE_COMPOSE")
[[ -f "$HARDEN_OVERRIDE" ]] && COMPOSE_ARGS+=(-f "$HARDEN_OVERRIDE")
COMPOSE_ARGS+=(-f "$TMPFS_OVERRIDE")

docker compose "${COMPOSE_ARGS[@]}" build "$FRONT_SVC"

msg "Restarting $FRONT_SVC…"
docker compose "${COMPOSE_ARGS[@]}" up -d "$FRONT_SVC"

# 5) Wait for frontend health (if healthcheck exists)
CID="$(docker compose "${COMPOSE_ARGS[@]}" ps -q "$FRONT_SVC")"
if [[ -n "$CID" ]]; then
  msg "Waiting for $FRONT_SVC to be healthy…"
  attempts=0; max_attempts=60
  while true; do
    state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
    if [[ "$state" == "healthy" ]]; then
      echo "   $FRONT_SVC: healthy ✅"
      break
    fi
    if [[ "$state" == "unhealthy" ]]; then
      echo "   $FRONT_SVC: UNHEALTHY ❌ — last health logs:"
      docker inspect "$CID" --format '{{range .State.Health.Log}}{{println .Output}}{{end}}' | tail -n 10 || true
      exit 1
    fi
    ((attempts+=1))
    (( attempts >= max_attempts )) && { echo "   Timeout (state=$state)"; docker logs --tail=200 "$CID" || true; exit 1; }
    sleep 2
  done
fi

# 6) Quick sanity checks
msg "Checking logs for nginx startup errors…"
docker logs --tail=50 "$CID" | grep -E 'nginx: \[emerg\]' && die "nginx emerg errors present"
echo "   no [emerg] errors — OK"

msg "Probing gzip header on / (Content-Encoding should be gzip)…"
curl -sI --compressed http://127.0.0.1:3000/ | tr -d '\r' | grep -iE 'HTTP/|Content-Encoding|Cache-Control' || true

msg "Done. Frontend gzip enabled, /tmp writable via tmpfs, container remains read-only."
