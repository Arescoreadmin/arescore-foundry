#!/usr/bin/env bash
set -euo pipefail

# always run from repo root
cd "$(dirname "$0")/.."

export PYTHONPATH=backend/frostgatecore

python -m uvicorn app.main:app --port 8001
