SHELL:=/bin/bash
.ONESHELL:

.PHONY: up down smoke logs ps rebuild nuke check env-core smoke-rag bench-rag rag-hits build test-e2e

# Compose file(s). Override like:
#   make up COMPOSE_FILES="compose.yml -f compose.staging.yml"
COMPOSE_FILES ?= infra/docker-compose.yml
COMPOSE = docker compose -f $(COMPOSE_FILES)

# Health endpoints. Override if your ports differ.
API_HEALTH ?= http://localhost:8000/health
FE_HEALTH  ?= http://localhost:3000/health
RAG_HEALTH ?= http://localhost:8000/healthz

# Curl flags: fail on non-2xx, retry transient errors, keep quiet unless broken.
CURLQ = curl -fsS --retry 15 --retry-all-errors --retry-delay 1

# Sentinel container helpers
SENTINEL_CONTAINER ?= sentinelcore
SENTINEL_EXEC      = docker exec -it $(SENTINEL_CONTAINER)
SENTINEL_EXEC_RAW  = docker exec -i $(SENTINEL_CONTAINER)

up:
	$(COMPOSE) up -d --build --wait

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs --no-log-prefix --tail=200

ps:
	$(COMPOSE) ps

rrebuild-orchestrator:
	docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml build --no-cache orchestrator
	docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml up -d orchestrator --force-recreate --no-deps
nuke:
	@printf "tearing everything down, volumes included...\n"
	$(COMPOSE) down -v --remove-orphans

# single source of truth; DO NOT define smoke anywhere else
smoke:
	@printf "waiting for API...\n"; \
	$(CURLQ) $(API_HEALTH) >/dev/null
	@printf "waiting for frontend...\n"; \
	$(CURLQ) $(FE_HEALTH) >/dev/null
	@echo "smoke: ok"

check:
	@printf "Scanning Makefile for duplicate target names...\n"; \
	awk -F':' '/^[a-zA-Z0-9_.-]+:/{print $$1}' Makefile \
	| sort | uniq -d | { read dups || exit 0; \
	if [ -n "$$dups" ]; then echo "Duplicate targets found:"; echo "$$dups"; exit 2; fi; }

env-core:
	@$(SENTINEL_EXEC) env | grep -E 'RAG_CACHE|RAG_QUERY_TTL' || true

smoke-rag:
	@$(SENTINEL_EXEC) python scripts/smoke_rag_cache.py || true

bench-rag:
	@$(SENTINEL_EXEC) python scripts/bench_rag_cache.py || true

rag-hits:
	@CID=$$(python -c 'import uuid; print(uuid.uuid4())'); \
	$(CURLQ) -H "X-Correlation-ID: $$CID" $(RAG_HEALTH) >/dev/null || true; \
	$(CURLQ) -H "X-Correlation-ID: $$CID" $(RAG_HEALTH) >/dev/null || true; \
	docker logs $(SENTINEL_CONTAINER) --since=5m | grep $$CID | grep -E "RAGCACHE (embed|ingest|query)" || true

# convenience wrappers matching what you tried
build:
	@$(MAKE) rebuild

test-e2e:
	@scripts/test_foundry.sh

.PHONY: test-all
test-all:
	./scripts/verify_stack.sh


doctor:
	@set -euo pipefail; \
	docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml config >/dev/null; \
	./scripts/verify_stack.sh; \
	echo "doctor: OK"


up-core:
	docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml up -d opa
	docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml up -d orchestrator --no-deps

down-core:
	docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml down --remove-orphans

