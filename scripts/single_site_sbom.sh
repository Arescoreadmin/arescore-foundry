#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ">>> Generating SBOMs + digests for SINGLE-SITE stack…"

PROJECT_NAME=arescore-foundry \
COMPOSE_FILES="-f compose.yml -f compose.federated.yml -f compose.single.yml" \
ARTIFACT_DIR="artifacts-single" \
bash scripts/report_sbom.sh

echo
echo "Artifacts written to ./artifacts-single:"
ls -1 artifacts-single
