#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/single_site_scenario_create.sh [name] [template] [description]
#
# Defaults:
#   name       = netplus-demo
#   template   = netplus
#   desc       = Single-site demo scenario

NAME="${1:-netplus-demo}"
TEMPLATE="${2:-netplus}"
DESC="${3:-Single-site demo scenario}"

echo ">>> Creating scenario:"
echo "    name:      ${NAME}"
echo "    template:  ${TEMPLATE}"
echo "    desc:      ${DESC}"

SCENARIO_ID="$(
  curl -fsS -X POST http://localhost:8080/api/scenarios \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg name "$NAME" --arg tmpl "$TEMPLATE" --arg desc "$DESC" \
         '{name: $name, template: $tmpl, description: $desc}')" \
  | jq -r '.id'
)"

echo ">>> Scenario created"
echo "ID=${SCENARIO_ID}"
