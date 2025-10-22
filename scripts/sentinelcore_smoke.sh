#!/usr/bin/env bash
set -euo pipefail

CID="$(python - <<'PY'
import uuid; print(uuid.uuid4())
PY
)"

echo "Health…"
docker exec -i sentinelcore python -c \
"import json,sys,urllib.request as u; r=u.urlopen('http://localhost:8001/health',timeout=2); print('status:', r.status, 'body:', r.read())"

echo "Embed…"
curl -sf -H "X-Correlation-ID: $CID" -H "content-type: application/json" \
  -d '{"text":"The   quick   brown    fox"}' http://localhost:8001/dev/embed >/dev/null

echo "Query x2…"
curl -sf -H "X-Correlation-ID: $CID" "http://localhost:8001/dev/q?q=ping%20pong&k=5" >/dev/null
curl -sf -H "X-Correlation-ID: $CID" "http://localhost:8001/dev/q?q=ping%20pong&k=5" >/dev/null

echo "Recent RAGCACHE hits:"
docker logs sentinelcore --since=2m | grep -E "RAGCACHE (embed|query)" | tail -n 10 || true

echo "Done."
