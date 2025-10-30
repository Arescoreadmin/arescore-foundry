#!/usr/bin/env bash
set -euo pipefail
declare -A cnt
pkg=""
while IFS= read -r line; do
  l="${line%%#*}"
  if [[ "$l" =~ ^[[:space:]]*package[[:space:]]+([a-zA-Z0-9_.]+) ]]; then
    pkg="${BASH_REMATCH[1]}"
  elif [[ -n "$pkg" && "$l" =~ ^[[:space:]]*default[[:space:]]+allow[[:space:]]*:= ]]; then
    cnt["$pkg"]=$(( ${cnt["$pkg"]:-0} + 1 ))
  fi
done < <(cat policies/*.rego 2>/dev/null || true)

fail=0
for k in "${!cnt[@]}"; do
  if (( cnt["$k"] > 1 )); then
    echo "❌ multiple defaults for '$k' (allow) — found ${cnt[$k]}" >&2
    fail=1
  fi
done
exit $fail
