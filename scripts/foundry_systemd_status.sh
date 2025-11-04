#!/usr/bin/env bash
set -euo pipefail
systemctl --no-pager status arescore-foundry || true
journalctl -u arescore-foundry -n 200 --no-pager || true
