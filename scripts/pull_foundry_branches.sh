#!/usr/bin/env bash
set -e

BRANCHES=("foundry-orchestrator" "foundry-api")

for b in "${BRANCHES[@]}"; do
  echo "[git] Updating branch $b..."
  git fetch origin "$b":"$b" || true
  git switch "$b"
  git pull origin "$b"
done

# land on API branch by default
git switch foundry-api
echo "[git] Done. Currently on branch: $(git branch --show-current)"
