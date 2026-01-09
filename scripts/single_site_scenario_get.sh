#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <scenario_id>" >&2
  exit 1
fi

SCENARIO_ID="$1"

echo ">>> Fetching scenario ${SCENARIO_ID}…"
curl -fsS "http://localhost:8080/api/scenarios/${SCENARIO_ID}" | jq .
