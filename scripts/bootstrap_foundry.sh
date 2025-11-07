#!/usr/bin/env bash
set -e

echo "[bootstrap] Ensuring base directories..."
mkdir -p audits usage templates scripts frontend

if [ ! -f .env ]; then
  echo "[bootstrap] Creating .env with placeholder values..."
  cat > .env << 'EOF'
DB_URL=sqlite:///foundry.db
S3_PATH=./s3-mock
CORE_URL=http://localhost:7001
SPEAR_URL=http://localhost:7002
EOF
else
  echo "[bootstrap] .env already exists, not touching it."
fi

echo "[bootstrap] Adding audits/ and usage/ to .gitignore (if not already)..."
grep -qxF "audits/" .gitignore 2>/dev/null || echo "audits/" >> .gitignore
grep -qxF "usage/" .gitignore 2>/dev/null || echo "usage/" >> .gitignore

echo "[bootstrap] Done."
