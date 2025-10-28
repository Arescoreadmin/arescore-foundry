SHELL := /bin/sh
.PHONY: up down smoke logs ps rebuild nuke check

# Compose file(s). Override like:
#   make up COMPOSE_FILES="compose.yml -f compose.staging.yml"
COMPOSE_FILES ?= infra/docker-compose.yml
COMPOSE = docker compose -f $(COMPOSE_FILES)

# Health endpoints. Override if your ports differ.
API_HEALTH ?= http://localhost:8000/health
FE_HEALTH  ?= http://localhost:3000/health

# Curl flags: fail on non-2xx, retry transient errors, keep quiet unless broken.
CURLQ = curl -fsS --retry 15 --retry-all-errors --retry-delay 1

up:
	$(COMPOSE) up -d --build --wait

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs --no-log-prefix --tail=200
