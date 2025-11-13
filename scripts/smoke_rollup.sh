#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://localhost:8087/health
curl -fsS http://localhost:8088/health
curl -fsS -X POST http://localhost:8087/create -H 'content-type: application/json' -d '{"type":"vxlan","vni":1001,"mtu":1600,"ports":[4789]}'
curl -fsS -X POST http://localhost:8088/provision -H 'content-type: application/json' -d '{"secure":true,"dscp":46,"codec":"opus"}'
