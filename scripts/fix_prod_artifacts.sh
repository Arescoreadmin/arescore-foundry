#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Repo: $ROOT"

#############################################
# 1) Fix compose.yml service stubs
#############################################

COMPOSE_FILE="compose.yml"

if [[ -f "$COMPOSE_FILE" ]]; then
  echo "==> Backing up $COMPOSE_FILE"
  cp "$COMPOSE_FILE" "${COMPOSE_FILE}.bak.$(date +%s)"

  echo "==> Removing stub services (consent_registry, evidence_bundler) from $COMPOSE_FILE (if needed)"
  python3 - <<'PY'
import pathlib, sys

try:
    import yaml
except Exception as e:
    print(f"ERROR: PyYAML not available: {e}", file=sys.stderr)
    sys.exit(1)

p = pathlib.Path("compose.yml")
data = yaml.safe_load(p.read_text()) or {}
services = data.get("services") or {}

changed = False

def should_drop(name, svc):
    if name not in {"consent_registry", "evidence_bundler"}:
        return False
    if not isinstance(svc, dict):
        return False
    # if it has image or build, it's real, leave it alone
    if any(k in svc for k in ("image", "build")):
        return False
    # only depends_on / empty counts as stub
    allowed = {"depends_on"}
    if set(svc.keys()).issubset(allowed):
        return True
    return False

for name in list(services.keys()):
    svc = services[name]
    if should_drop(name, svc):
        print(f"   - Removing stub service '{name}' from compose.yml")
        services.pop(name)
        changed = True

if changed:
    data["services"] = services
    p.write_text(yaml.safe_dump(data, sort_keys=False))
    print("==> compose.yml updated")
else:
    print("==> compose.yml: no stub services to remove; nothing changed.")
PY
else
  echo "WARN: $COMPOSE_FILE not found, skipping compose fix"
fi

#############################################
# 2) Fix build-and-push workflow header
#############################################

WF=".github/workflows/build-and-push.yml"

if [[ -f "$WF" ]]; then
  echo "==> Backing up $WF"
  cp "$WF" "${WF}.bak.$(date +%s)"

  echo "==> Stripping stray shell lines from top of $WF (the 'delete that step' junk)"
  sed -i \
    -e '/^delete that step, save, exit$/d' \
    -e '/^git add .github\/workflows\/build-and-push.yml$/d' \
    -e '/^git commit -m "ci: remove debug step"$/d' \
    -e '/^git push$/d' \
    "$WF"

  echo "==> Verifying YAML parses"
  python3 - <<'PY'
import sys, yaml
from pathlib import Path

p = Path(".github/workflows/build-and-push.yml")
try:
    yaml.safe_load(p.read_text())
    print("==> YAML OK: .github/workflows/build-and-push.yml")
except Exception as e:
    print("ERROR: YAML parse failed for build-and-push.yml:", e, file=sys.stderr)
    sys.exit(1)
PY
else
  echo "WARN: $WF not found, skipping workflow fix"
fi

echo "==> Done. Stage and commit if it all looks sane."
