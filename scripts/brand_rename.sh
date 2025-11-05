#!/usr/bin/env bash
set -euo pipefail

# Simple branding rename script
# Company: Sentinel -> FrostGate
# Product: Foundry (kept)
#
# Run from repo root:
#   chmod +x scripts/brand_rename.sh
#   ./scripts/brand_rename.sh --dry-run   # see matches
#   ./scripts/brand_rename.sh             # apply replacements

DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

echo "[*] Using git grep to find branding occurrences..."

# Tokens and their replacements
TOKENS=(
  "Sentinel Foundry"
  "sentinel-foundry"
  "SENTINEL_FOUNDRY"
  "Sentinel"
)

REPLACEMENTS=(
  "FrostGate Foundry"
  "frostgate-foundry"
  "FROSTGATE_FOUNDRY"
  "FrostGate"
)

# Show where things are before touching anything
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
echo "[*] Applying in-place replacements..."

# Get list of text files tracked by git
FILES=$(git grep -Il 'Sentinel\|sentinel-foundry\|SENTINEL_FOUNDRY' || true)

if [[ -z "$FILES" ]]; then
  echo "[!] No files to modify. Exiting."
  exit 0
fi

for f in $FILES; do
  # Skip artifacts if you want to regenerate them instead
  case "$f" in
    artifacts/*|artifacts-single/*)
      echo "[*] Skipping generated file: $f"
      continue
      ;;
  esac

  tmp="${f}.brand_rename_tmp"

  cp "$f" "$tmp"

  # Apply each replacement in order
  for i in "${!TOKENS[@]}"; do
    from="${TOKENS[$i]}"
    to="${REPLACEMENTS[$i]}"
    # Use perl for safer in-place replace with spaces and mixed case
    perl -pe "s/\Q$from\E/$to/g" "$tmp" > "${tmp}.out"
    mv "${tmp}.out" "$tmp"
  done

  mv "$tmp" "$f"
done

echo
echo "[*] Done. Run 'git diff' to inspect changes."
