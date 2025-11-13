#!/usr/bin/env bash
set -euo pipefail

nats stream add overlay_cmd --subjects overlay.cmd.* --storage file --retention limits --max-msgs=-1 --max-bytes=-1 --replicas 1 || true
nats stream add overlay_evt --subjects overlay.evt.* --storage file --retention limits --max-msgs=-1 --max-bytes=-1 --replicas 1 || true
nats consumer add overlay_cmd orchestrator --filter overlay.cmd.* --ack explicit || true
nats consumer add overlay_evt overlay --filter overlay.evt.* --ack explicit || true
