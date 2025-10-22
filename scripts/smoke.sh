#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"

# auto-detect prefix: try "" then "/api"
detect_prefix() {
  for p in "" "/api"; do
    if curl -fsS "${BASE}${p}/health" >/dev/null 2>&1; then
      echo "$p"
      return 0
    fi
  done
  echo "Failed to detect API prefix at $BASE" >&2
  exit 1
}

PREFIX="$(detect_prefix)"
echo "Using BASE=$BASE PREFIX=$PREFIX"

# health
curl -fsS "$BASE$PREFIX/health"

# embed (twice, should be identical if cache works)
curl -fsS -X POST "$BASE$PREFIX/dev/embed" \
  -H 'content-type: application/json' -d '{"text":"ping"}' > /tmp/e1.json
curl -fsS -X POST "$BASE$PREFIX/dev/embed" \
  -H 'content-type: application/json' -d '{"text":"ping"}' > /tmp/e2.json
diff -u /tmp/e1.json /tmp/e2.json || {
  echo "embed responses differ. Your cache layer is lying to you." >&2
  exit 2
}

# query (twice, should be identical if TTL cache works)
curl -fsS -X POST "$BASE$PREFIX/dev/q" \
  -H 'content-type: application/json' -d '{"q":"x"}' > /tmp/q1.json
curl -fsS -X POST "$BASE$PREFIX/dev/q" \
  -H 'content-type: application/json' -d '{"q":"x"}' > /tmp/q2.json
diff -u /tmp/q1.json /tmp/q2.json || {
  echo "query responses differ. Either nondeterminism or busted cache." >&2
  exit 3
}

echo "Smoke OK ✅"
