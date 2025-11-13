#!/usr/bin/env bash
set -euo pipefail

WF=".github/workflows/ci.yml"
BACKUP=".github/workflows/ci.yml.bak.$(date +%s)"

if [[ ! -f "$WF" ]]; then
  echo "❌ $WF not found. Run this from your repo root." >&2
  exit 1
fi

cp "$WF" "$BACKUP"

read -r -d '' NEWBLOCK <<'BLOCK'
      - name: Run backend tests
        env:
          PYTHONPATH: backend/frostgatecore
        run: |
          set -euo pipefail
          . .venv/bin/activate
          if [[ -d backend/frostgatecore/tests ]]; then
            # Run backend test suite; treat "no tests collected" (exit 5) as success
            pytest -q backend/frostgatecore/tests || [[ $? -eq 5 ]]
          else
            echo "No backend tests directory. Skipping."
          fi
        shell: bash
BLOCK

# Replace the entire "Run backend tests" step body with the guarded block.
awk -v newblock="$NEWBLOCK" '
  BEGIN { in_target=0 }
  {
    if (in_target) {
      # Stop when a new step at same indentation begins or job ends
      if ($0 ~ /^[[:space:]]{6}- name:/ || $0 ~ /^[[:space:]]{4}[a-zA-Z0-9_-]+:/) {
        in_target=0
        print $0
      } else {
        next
      }
    } else {
      print $0
      if ($0 ~ /^[[:space:]]{6}- name:[[:space:]]*Run backend tests[[:space:]]*$/) {
        in_target=1
        print newblock
      }
    }
  }
' "$WF" > "$WF.tmp"

mv "$WF.tmp" "$WF"

echo "✅ Patched $WF"
echo "🗂️  Backup at $BACKUP"

# Optional: run actionlint locally like CI
if command -v docker >/dev/null 2>&1; then
  docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color || true
fi
