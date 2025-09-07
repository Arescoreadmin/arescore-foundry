#!/usr/bin/env bash
# scripts/prodize.sh
set -euo pipefail

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="$ROOT/infra"
FRONTEND_DIR="$ROOT/frontend"
SCRIPTS_DIR="$ROOT/scripts"

BASE="$INFRA/docker-compose.yml"
OVR="$INFRA/docker-compose.override.yml"
HLT="$INFRA/docker-compose.health.yml"
DEP="$INFRA/docker-compose.depends.yml"
SEC="$INFRA/docker-compose.security.yml"

mkdir -p "$FRONTEND_DIR" "$SCRIPTS_DIR" "$INFRA"

compose_cmd(){ 
  local files=(-f "$BASE")
  [[ -f "$OVR" ]] && files+=(-f "$OVR")
  [[ -f "$HLT" ]] && files+=(-f "$HLT")
  [[ -f "$DEP" ]] && files+=(-f "$DEP")
  [[ -f "$SEC" ]] && files+=(-f "$SEC")
  docker compose "${files[@]}" "$@"
}

# ---------- 1) Bake hardened nginx.conf ----------
say "Writing frontend/nginx.conf (hardened)"
cat > "$FRONTEND_DIR/nginx.conf" <<'NGINX'
# Global/http context directives allowed in conf.d includes
# Limit API burst (10 r/s, burst 20) – adjust to your needs
limit_req_zone $binary_remote_addr zone=api_ratelimit:10m rate=10r/s;

# JSON logs to stdout/stderr
log_format json_combined escape=json
  '{'
  '"time":"$time_iso8601",'
  '"remote_addr":"$remote_addr",'
  '"request":"$request",'
  '"status":$status,'
  '"body_bytes_sent":$body_bytes_sent,'
  '"request_time":$request_time,'
  '"upstream_response_time":"$upstream_response_time",'
  '"upstream_status":"$upstream_status",'
  '"http_referer":"$http_referer",'
  '"http_user_agent":"$http_user_agent"'
  '}';

server {
  listen 8080;
  server_name _;

  # Static files
  root /usr/share/nginx/html;
  index index.html;

  # Security headers (tune CSP as your app requires)
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options DENY always;
  add_header Referrer-Policy no-referrer-when-downgrade always;
  add_header X-XSS-Protection "1; mode=block" always;
  # Example minimal CSP (adjust or comment out if it breaks assets)
  add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' data: blob:;" always;

  # Logging to stdout/stderr
  access_log /dev/stdout json_combined;
  error_log  /dev/stderr warn;

  # Performance
  sendfile on;
  tcp_nopush on;
  tcp_nodelay on;
  keepalive_timeout 65;

  # gzip (works on nginx alpine)
  gzip on;
  gzip_types text/plain text/css application/json application/javascript application/xml image/svg+xml;
  gzip_min_length 1024;

  # WebSocket upgrade
  map $http_upgrade $connection_upgrade { default upgrade; '' close; }

  # SPA route
  location / {
    try_files $uri /index.html;
  }

  # Lightweight ready
  location = /ready {
    default_type application/json;
    return 200 "{\"ready\":true}";
  }

  # API proxy to orchestrator with timeouts + retries + WS + rate limit
  location /api/ {
    limit_req zone=api_ratelimit burst=20 nodelay;

    proxy_pass http://orchestrator:8000/;
    proxy_http_version 1.1;

    # WebSockets
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;

    # Buffers to avoid 502 on large headers/bodies
    proxy_buffers 16 16k;
    proxy_buffer_size 16k;

    # Tight connect + moderate read/send; adjust if backend slow
    proxy_connect_timeout 1s;
    proxy_send_timeout    6s;
    proxy_read_timeout    6s;

    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 3;
  }
}
NGINX

# ---------- 2) Ensure compose override mounts nginx.conf ----------
if ! grep -q "/etc/nginx/conf.d/default.conf" "${OVR:-/dev/null}" 2>/dev/null; then
  say "Writing infra/docker-compose.override.yml (mount nginx.conf)"
  cat > "$OVR" <<'YML'
services:
  frontend:
    volumes:
      - ../frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
YML
fi

# ---------- 3) Healthchecks for all services ----------
say "Writing infra/docker-compose.health.yml"
cat > "$HLT" <<'YML'
services:
  frontend:
    healthcheck:
      test: ["CMD-SHELL", "(curl -fsS http://localhost:8080/ready || wget -qO- http://localhost:8080/ready) >/dev/null || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 15
      start_period: 10s

  orchestrator:
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import sys,urllib.request,socket; socket.setdefaulttimeout(2); urllib.request.urlopen('http://localhost:8000/health'); sys.exit(0)\" || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 30
      start_period: 5s

  log_indexer:
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import sys,urllib.request,socket; socket.setdefaulttimeout(2); urllib.request.urlopen('http://localhost:8080/health'); sys.exit(0)\" || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 30
      start_period: 5s
YML

# ---------- 4) Startup ordering ----------
say "Writing infra/docker-compose.depends.yml (frontend waits for orchestrator healthy)"
cat > "$DEP" <<'YML'
services:
  frontend:
    depends_on:
      orchestrator:
        condition: service_healthy
YML

# ---------- 5) Security hardening + resource limits ----------
say "Writing infra/docker-compose.security.yml"
cat > "$SEC" <<'YML'
services:
  frontend:
    read_only: true
    tmpfs: [/tmp]
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
    # local-only resource hints (compose): adjust to your machine
    mem_limit: 512m
    cpus: "0.75"

  orchestrator:
    read_only: true
    tmpfs: [/tmp]
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
    mem_limit: 1g
    cpus: "1.00"

  log_indexer:
    read_only: true
    tmpfs: [/tmp]
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
    mem_limit: 512m
    cpus: "0.50"
YML

# ---------- 6) Patch log_indexer with HTTP health server ----------
IDX="$ROOT/log_indexer/indexer.py"
if [[ -f "$IDX" ]] && ! grep -q '# --- HEALTHCHECK PATCH START ---' "$IDX"; then
  say "Patching log_indexer/indexer.py with HTTP /health on :8080"
  cp -n "$IDX" "$IDX.bak" || true
  cat >> "$IDX" <<'PY'
# --- HEALTHCHECK PATCH START ---
# Minimal HTTP health/ready/live on :8080; returns 500 if no progress for HEALTH_STALE_AFTER seconds (default 600s).
try:
    import time, json, os, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    _hc_start = time.time(); _hc_last_ok = _hc_start
    def mark_indexer_progress():
        global _hc_last_ok; _hc_last_ok = time.time()
    class _HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/health", "/ready", "/live"):
                age = time.time() - _hc_last_ok
                stale_after = float(os.getenv("HEALTH_STALE_AFTER", "600"))
                status = 200 if age < stale_after else 500
                body = json.dumps({"status":"ok" if status==200 else "stale",
                                   "uptime_s":round(time.time()-_hc_start,3),
                                   "age_since_last_ok_s":round(age,3)})
                self.send_response(status); self.send_header("Content-Type","application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body.encode("utf-8"))
            else: self.send_response(404); self.end_headers()
        def log_message(self, *a, **k): return
    def _health_server():
        port = int(os.getenv("HEALTH_PORT", "8080"))
        srv = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
        srv.daemon_threads = True; srv.serve_forever()
    threading.Thread(target=_health_server, daemon=True).start()
except Exception:  # never crash the indexer for health server issues
    pass
# --- HEALTHCHECK PATCH END ---
PY
else
  say "indexer.py already patched or missing; skipping health server patch"
fi

# ---------- 7) Robust smoke.sh ----------
say "Writing scripts/smoke.sh (robust)"
cat > "$SCRIPTS_DIR/smoke.sh" <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="$ROOT/infra"
DC=(-f "$INFRA/docker-compose.yml")
[[ -f "$INFRA/docker-compose.override.yml" ]] && DC+=(-f "$INFRA/docker-compose.override.yml")
[[ -f "$INFRA/docker-compose.health.yml"   ]] && DC+=(-f "$INFRA/docker-compose.health.yml")
[[ -f "$INFRA/docker-compose.depends.yml"  ]] && DC+=(-f "$INFRA/docker-compose.depends.yml")
[[ -f "$INFRA/docker-compose.security.yml" ]] && DC+=(-f "$INFRA/docker-compose.security.yml")

have_wait(){
  docker compose version 2>/dev/null | awk 'match($0,/v2\.([0-9]+)/,m){ if (m[1] >= 20) {print "yes"} }' | grep -q yes
}

echo "==> Up"
if have_wait; then
  docker compose "${DC[@]}" up -d --build --wait --wait-timeout 90
else
  docker compose "${DC[@]}" up -d --build
fi

# Probes
curl -fsS http://localhost:3000/ready >/dev/null
curl -fsS http://localhost:3000/api/ready >/dev/null
curl -fsS http://localhost:8000/health >/dev/null
curl -fsS http://localhost:8080/health >/dev/null
echo "==> PASS"
BASH
chmod +x "$SCRIPTS_DIR/smoke.sh"

# ---------- 8) Enforce LF endings ----------
say "Writing .gitattributes (LF for scripts/YAML)"
cat > "$ROOT/.gitattributes" <<'GIT'
*.sh text eol=lf
*.bash text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
Dockerfile* text eol=lf
GIT

# ---------- 9) Bring everything up & verify ----------
say "Bringing stack up with all overrides"
compose_cmd up -d --build

# Use --wait when available
if docker compose version 2>/dev/null | grep -qE 'v2\.(2[0-9]|[3-9][0-9])'; then
  compose_cmd up -d --wait --wait-timeout 90 || true
fi

say "Health status"
compose_cmd ps

say "Smoke checks"
bash "$SCRIPTS_DIR/smoke.sh"

say "CURL checks"
curl -fsS http://localhost:3000/ready && echo
curl -fsS http://localhost:3000/api/ready && echo
curl -fsS http://localhost:8080/health && echo

say "Done. Consider committing these changes."
