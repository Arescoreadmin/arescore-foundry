#!/usr/bin/env bash
set -euo pipefail

# Cleanup script for Sentinel → FrostGate backend naming
#
# Fixes all the "sentinelfrostgatecore" / "sentinelcore" leftovers and env vars.
#
# Usage:
#   chmod +x scripts/brand_residual_fix.sh
#   ./scripts/brand_residual_fix.sh --dry-run   # show matches only
#   ./scripts/brand_residual_fix.sh             # apply replacements

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

echo "[*] Scanning for residual 'sentinel*core' references..."

TOKENS=(
  "sentinelfrostgatecore"   # monster
  "sentinelcore"            # old name
  "SENTINELFROSTGATECORE"   # if it exists
  "SENTINELCORE"            # old env / hostnames
)

REPLACEMENTS=(
  "frostgatecore"
  "frostgatecore"
  "FROSTGATECORE"
  "FROSTGATECORE"
)

# Show matches first
for t in "${TOKENS[@]}"; do
  echo
  echo "=== Matches for: '$t' ==="
  git grep -n --color=always -- "$t" || true
done

if $DRY_RUN; then
  echo
  echo "[*] Dry run only. No files modified."
  exit 0
fi

echo
echo "[*] Collecting files to modify..."

FILES=$(git grep -Il 'sentinelfrostgatecore\|sentinelcore\|SENTINELCORE\|SENTINELFROSTGATECORE' || true)

if [[ -z "$FILES" ]]; then
  echo "[!] No files to modify. Exiting."
  exit 0
fi

for f in $FILES; do
  # Skip generated stuff if any
  case "$f" in
    artifacts/*|artifacts-single/*)
      echo "[*] Skipping generated file: $f"
      continue
      ;;
  esac

  tmp="${f}.brand_residual_tmp"
  cp "$f" "$tmp"

  for i in "${!TOKENS[@]}"; do
    from="${TOKENS[$i]}"
    to="${REPLACEMENTS[$i]}"
    perl -pe "s/\Q$from\E/$to/g" "$tmp" > "${tmp}.out"
    mv "${tmp}.out" "$tmp"
  done

  mv "$tmp" "$f"
done

echo
echo "[*] Replacement complete. Review with:"
echo "    git diff"
