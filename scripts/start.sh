#!/bin/bash
set -e

DIR=$(dirname "$0")/..
cd "$DIR"

docker compose -f infra/docker-compose.yml --env-file infra/.env.example up -d
