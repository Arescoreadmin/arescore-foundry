#!/usr/bin/env bash
set -euo pipefail

# 1) GitHub Actions workflow lint
docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color

# 2) Python lint/format (optional but you know you should)
if command -v ruff >/dev/null 2>&1; then
  ruff check app tests
fi
if command -v black >/dev/null 2>&1; then
  black --check app tests
fi

# 3) Unit tests
pytest -q
echo "✅ CI-local passed."
