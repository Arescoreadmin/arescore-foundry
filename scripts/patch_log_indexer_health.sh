#!/usr/bin/env bash
set -euo pipefail
ACTION="${1:-apply}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="${INFRA:-$ROOT/infra}"
INDEXER_SRC="${INDEXER_SRC:-$ROOT/log_indexer/indexer.py}"
HLT="${HLT:-$INFRA/docker-compose.health.yml}"
BASE="$INFRA/docker-compose.yml"; OVR="$INFRA/docker-compose.override.yml"

compose_cmd(){ local f=(-f "$BASE"); [[ -f "$OVR" ]]&&f+=(-f "$OVR"); [[ -f "$HLT" ]]&&f+=(-f "$HLT"); docker compose "${f[@]}" "$@"; }
wait_health(){ local s="$1" n="${2:-60}"; for _ in $(seq 1 "$n"); do
  local id; id="$(compose_cmd ps -q "$s" | tr -d '\r')"; [[ -n "$id" ]]||{ sleep 1; continue; }
  local st; st="$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo none)"
  [[ "$st" == healthy ]] && { echo "OK: $s healthy"; return 0; }; sleep 1; done; echo "WARN: $s not healthy yet"; return 1; }

patch_indexer(){
  [[ -f "$INDEXER_SRC" ]] || { echo "ERROR: $INDEXER_SRC not found"; exit 1; }
  grep -q '# --- HEALTHCHECK PATCH START ---' "$INDEXER_SRC" && { echo "indexer.py already patched"; return 0; }
  cp -n "$INDEXER_SRC" "$INDEXER_SRC.bak" || true
  cat >> "$INDEXER_SRC" <<'PY'
# --- HEALTHCHECK PATCH START ---
# Minimal HTTP health/ready/live on :8080; becomes 500 if no progress for HEALTH_STALE_AFTER seconds (default 120s).
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
                status = 200 if age < float(os.getenv("HEALTH_STALE_AFTER", "120")) else 500
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
except Exception: pass
# --- HEALTHCHECK PATCH END ---
PY
  echo "✓ Patched $INDEXER_SRC (backup at $INDEXER_SRC.bak)"
}

write_health_override(){
  mkdir -p "$(dirname "$HLT")"
  if [[ ! -f "$HLT" ]]; then echo "services:" > "$HLT"; fi
  # replace existing log_indexer health block (if any)
  perl -0777 -pe 's/\n?\s*# LOG_INDEXER HEALTH PATCH START.*?# LOG_INDEXER HEALTH PATCH END\n?//s' -i "$HLT" || true
  cat >> "$HLT" <<'YML'
  # LOG_INDEXER HEALTH PATCH START (auto)
  log_indexer:
    environment:
      # raise if your loop doesn’t call mark_indexer_progress yet
      HEALTH_STALE_AFTER: "600"
      # change to 8081 if something else binds 8080
      HEALTH_PORT: "8080"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import sys,urllib.request,socket; socket.setdefaulttimeout(2); urllib.request.urlopen('http://localhost:8080/health'); sys.exit(0)\" || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 5s
  # LOG_INDEXER HEALTH PATCH END
YML
  echo "✓ Wrote/updated $HLT"
}

apply(){
  patch_indexer
  write_health_override
  echo "==> Rebuild + up log_indexer"
  compose_cmd up -d --build log_indexer
  echo "==> Wait for health"
  wait_health log_indexer || true
  echo "==> Probe /health inside container"
  compose_cmd exec -T log_indexer sh -lc "python - <<'PY'
import urllib.request; print(urllib.request.urlopen('http://localhost:8080/health').read().decode())
PY"
}

revert(){
  echo "==> Revert health override"
  if [[ -f "$HLT" ]]; then
    perl -0777 -pe 's/\n?\s*# LOG_INDEXER HEALTH PATCH START.*?# LOG_INDEXER HEALTH PATCH END\n?//s' -i "$HLT" || true
    # remove file if it only contains 'services:' or is empty
    (grep -q '[^[:space:]]' "$HLT" && ! grep -qE '^\s*services:\s*$' "$HLT") || rm -f "$HLT"
  fi
  echo "==> Restore indexer.py"
  if [[ -f "$INDEXER_SRC.bak" ]]; then mv -f "$INDEXER_SRC.bak" "$INDEXER_SRC"; else
    perl -0777 -pe 's/# --- HEALTHCHECK PATCH START ---.*?# --- HEALTHCHECK PATCH END ---\n?//s' -i "$INDEXER_SRC" || true
  fi
  compose_cmd up -d --build log_indexer
  echo "Done."
}

case "$ACTION" in
  apply) apply ;;
  revert) revert ;;
  *) echo "usage: $0 {apply|revert}"; exit 2 ;;
esac
