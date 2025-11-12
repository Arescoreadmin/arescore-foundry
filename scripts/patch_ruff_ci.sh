#!/usr/bin/env bash
set -euo pipefail
WF=".github/workflows/ci.yml"
B=".github/workflows/ci.yml.bak.$(date +%s)"
cp "$WF" "$B"
awk '
  { print }
  $0 ~ /^[[:space:]]*- name:[[:space:]]*Ruff[[:space:]]*\(Python\)/ { mode=1; next }
  mode==1 && $0 ~ /^[[:space:]]*run:[[:space:]]*\|/ {
    print "        run: |"
    print "          set -euo pipefail"
    print "          if git ls-files '\\''*.py'\\'' | grep -q .; then"
    print "            ruff check --output-format=github --fix --exit-non-zero-on-fix ."
    print "          else"
    print "            echo \"No Python files. Skipping ruff.\""
    print "          fi"
    print "        shell: bash"
    mode=2; next
  }
  mode==1 { next }
  mode==2 && $0 ~ /^[[:space:]]*shell:[[:space:]]*bash/ { next }
' "$WF" > "$WF.tmp"
mv "$WF.tmp" "$WF"
echo "Patched $WF (backup at $B)"
