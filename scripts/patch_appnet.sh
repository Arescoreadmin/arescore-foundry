#!/usr/bin/env bash
set -euo pipefail

FILE="infra/docker-compose.override.yml"
BACKUP="${FILE}.bak.$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$FILE" ]; then
  echo "❌ ${FILE} not found. Run from repo root." >&2
  exit 1
fi

echo "📦 Backing up ${FILE} -> ${BACKUP}"
cp -f "$FILE" "$BACKUP"

# Use a dockerized Python to avoid host deps and preserve ordering/comments with ruamel.yaml
echo "🛠  Patching services: remove container_name, add networks: [appnet]…"
docker run --rm -i \
  -v "$PWD":/work \
  -w /work \
  python:3.11-slim bash -lc '
    set -e
    python - <<PY
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pathlib import Path

p = Path("infra/docker-compose.override.yml")
yaml = YAML()
yaml.preserve_quotes = True
data = yaml.load(p.read_text())

if not isinstance(data, dict) or "services" not in data:
    raise SystemExit("override file has no top-level `services` key")

changed = False
services = data["services"]

for name, svc in list(services.items()):
    if not isinstance(svc, dict):
        continue

    # 1) remove container_name
    if "container_name" in svc:
        del svc["container_name"]
        changed = True

    # 2) ensure networks includes appnet
    nets = svc.get("networks")
    if nets is None:
        svc["networks"] = ["appnet"]
        changed = True
    elif isinstance(nets, list):
        if "appnet" not in nets:
            nets.append("appnet")
            changed = True
    elif isinstance(nets, dict):
        # convert dict-style networks to list of keys and append appnet
        keys = list(nets.keys())
        if "appnet" not in keys:
            keys.append("appnet")
            changed = True
        svc["networks"] = keys

if changed:
    yaml.dump(data, p.open("w"))
    print("patched: yes")
else:
    print("patched: no changes")
PY
  ' >/dev/null

# Normalize line endings (in case Windows CRLF snuck in)
sed -i 's/\r$//' "$FILE"

echo "🔎 Validating docker compose config…"
docker compose -f infra/docker-compose.yml -f "$FILE" config --quiet || {
  echo "❌ Validation failed. Restoring backup."
  cp -f "$BACKUP" "$FILE"
  exit 1
}

echo "✅ Patch complete."
echo "   • Removed container_name from all services"
echo "   • Ensured networks: [appnet] on every service"
echo "   • Backup: ${BACKUP}"
