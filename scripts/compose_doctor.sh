# scripts/compose_doctor.sh
#!/usr/bin/env bash
set -euo pipefail

BASE=infra/docker-compose.yml
OVR=infra/compose.opa.yml

echo "==> Quick sanity: show file sizes and CRLF"
for f in "$BASE" "$OVR"; do
  [[ -f "$f" ]] || { echo "missing $f"; exit 2; }
  wc -l "$f"
  if grep -n $'\r' "$f" >/dev/null; then
    echo "   CRLF found in $f -> fixing"
    sed -i 's/\r$//' "$f"
  fi
done

echo "==> Scan for tabs / control chars (bad in YAML)"
for f in "$BASE" "$OVR"; do
  if grep -nP $'\t' "$f" >/dev/null; then echo "   TABS in $f:"; grep -nP $'\t' "$f"; fi
  if grep -nP '[\x00-\x08\x0B\x0C\x0E-\x1F]' "$f" >/dev/null; then
    echo "   CONTROL CHARS in $f:"; grep -nP '[\x00-\x08\x0B\x0C\x0E-\x1F]' "$f"
  fi
done

echo "==> Try compose config to capture parser error"
ERR=$(mktemp)
if docker compose -f "$BASE" -f "$OVR" config >/dev/null 2>"$ERR"; then
  echo "✅ compose parse OK"
  exit 0
fi

echo "❌ compose parse failed — analyzing…"
cat "$ERR"

# Extract file + line like: yaml: line 71: did not find expected key
LINE=$(grep -oE 'line [0-9]+' "$ERR" | awk '{print $2}' || true)
if [[ -n "${LINE:-}" ]]; then
  echo; echo "==> Suspect window in $BASE around line $LINE"
  nl -ba "$BASE" | sed -n "$((LINE-7)),$((LINE+7))p" || true
else
  echo; echo "==> Could also be in override; showing both files tail/head"
  echo "--- $BASE (head 120) ---"; nl -ba "$BASE" | sed -n '1,120p'
  echo "--- $OVR (cat) ---"; nl -ba "$OVR" | sed -n '1,200p'
fi

echo; echo "==> Searching for obvious shell junk that breaks YAML"
PAT='( >/dev/null|>>|<<|curl |docker compose |for i in {| && | \|\| )'
for f in "$BASE" "$OVR"; do
  if grep -nE "$PAT" "$f" >/dev/null; then
    echo "   Suspicious lines in $f:"; grep -nE "$PAT" "$f"
  fi
done

echo; echo "==> Auto-fix: remove known bad paste lines in override; leave base for manual review"
# Remove lines that look like a broken shell paste in override (saw this earlier)
sed -i '/compose\.yml -f infra\/compose\.opa\.yml/d;/\/dev\/null/d' "$OVR"

# Re-try parse
if docker compose -f "$BASE" -f "$OVR" config >/dev/null 2>"$ERR"; then
  echo "✅ compose parse OK after override cleanup"
  exit 0
else
  echo "❌ still failing; focus on lines shown above in $BASE (around the reported line)."
  exit 1
fi
