#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MODELS_FILE="services/spawn_service/app/models.py"

if [[ ! -f "$MODELS_FILE" ]]; then
  echo "[!] Cannot find $MODELS_FILE. Are you in the right repo?"
  exit 1
fi

echo "[*] Patching $MODELS_FILE to replace JSONB with portable JSON for SQLite..."

# 1) Fix the import:
#    from sqlalchemy.dialects.postgresql import JSONB, UUID
#    -> from sqlalchemy import JSON
#       from sqlalchemy.dialects.postgresql import UUID
sed -i 's/from sqlalchemy.dialects.postgresql import JSONB, UUID/from sqlalchemy import JSON\
from sqlalchemy.dialects.postgresql import UUID/' "$MODELS_FILE"

# 2) Replace JSONB type usages with JSON
sed -i 's/JSONB/JSON/g' "$MODELS_FILE"

echo "[+] Patch complete. Current JSON usage in models:"
rg -n "JSON" "$MODELS_FILE" || true

