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
	docker compose -f infra/docker-compose.yml up -d --build --wait

down:
	docker compose -f infra/docker-compose.yml down -v

logs:
	docker compose -f infra/docker-compose.yml logs --no-log-prefix --tail=200

ps:
	docker compose -f infra/docker-compose.yml ps

rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d --wait

nuke:
	@printf "tearing everything down, volumes included...\n"
	$(COMPOSE) down -v --remove-orphans

# single source of truth; DO NOT define smoke anywhere else
smoke:
	@printf "waiting for API...\n"; \
	  curl -fsS --retry 15 --retry-all-errors --retry-delay 1 http://localhost:8000/health >/dev/null
	@printf "waiting for frontend...\n"; \
	  curl -fsS --retry 15 --retry-all-errors --retry-delay 1 http://localhost:3000/health >/dev/null
	@echo "smoke: ok"
# sanity check to help humans find accidental duplicate targets
check:
	@printf "Scanning Makefile for duplicate target names...\n"; \
	awk -F':' '/^[a-zA-Z0-9_.-]+:/{print $$1}' Makefile \
	| sort | uniq -d | { read dups || exit 0; \
	if [ -n "$$dups" ]; then echo "Duplicate targets found:"; echo "$$dups"; exit 2; fi; }
