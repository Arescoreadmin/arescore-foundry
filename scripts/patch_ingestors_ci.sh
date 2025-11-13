#!/usr/bin/env bash
set -euo pipefail

WF=".github/workflows/ci.yml"
BACKUP=".github/workflows/ci.yml.bak.$(date +%s)"

if [[ ! -f "$WF" ]]; then
  echo "❌ $WF not found. Run this from your repo root." >&2
  exit 1
fi

cp "$WF" "$BACKUP"

# New guarded block for the ingestors test step
read -r -d '' NEWBLOCK <<'BLOCK'
        run: |
          set -euo pipefail
          . .venv/bin/activate
          if [[ -d services/ingestors/tests ]]; then
            pytest -q services/ingestors/tests || [[ $? -eq 5 ]]
          else
            echo "No ingestors tests directory. Skipping."
          fi
        shell: bash
BLOCK

awk -v newblock="$NEWBLOCK" '
  BEGIN { skipping = 0 }
  {
    if (skipping) {
      # Stop skipping at the start of the next step or when indentation decreases
      if ($0 ~ /^[[:space:]]{6}- name:/ || $0 !~ /^[[:space:]]{6}/) {
        skipping = 0
        print $0
      } else {
        next
      }
    } else {
      print $0
      if ($0 ~ /^[[:space:]]{6}- name:[[:space:]]*Run ingestors tests[[:space:]]*$/) {
        # Consume following lines belonging to this step until next step boundary,
        # and replace them with our guarded run+shell block.
        # The very next line is typically "run:"; we replace the whole block.
        skipping = 1
        print newblock
      }
    }
  }
' "$WF" > "$WF.tmp"

mv "$WF.tmp" "$WF"

echo "✅ Patched: $WF"
echo "🗂️  Backup: $BACKUP"
