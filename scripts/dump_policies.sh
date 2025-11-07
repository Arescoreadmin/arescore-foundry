#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
cd "$(dirname "$0")/.."

echo "[dump_policies] Scanning for .rego files under ./policies and ./_container_policies"
echo

FOUND=0

for dir in policies _container_policies; do
  if [ -d "$dir" ]; then
    echo "[dump_policies] Directory: $dir"
    echo

    for f in "$dir"/*.rego; do
      # handle "no matches" case without error
      if [ ! -e "$f" ]; then
        continue
      fi

      FOUND=1
      echo "=============================="
      echo "FILE: $f"
      echo "=============================="
      cat "$f"
      echo
      echo
    done
  fi
done

if [ "$FOUND" -eq 0 ]; then
  echo "[dump_policies] No .rego files found in ./policies or ./_container_policies"
fi
