# Makefile
SHELL := /bin/bash
.ONESHELL:
.PHONY: up down logs ps rebuild-frontend help

INFRA := infra/docker-compose.yml
ENV   := infra/.env

# default target: 'make' shows help
help:
	@echo "Targets:"
	@echo "  make up               - build and start all services"
	@echo "  make down             - stop and remove orphans"
	@echo "  make logs             - follow logs"
	@echo "  make ps               - list services"
	@echo "  make rebuild-frontend - rebuild only 'frontend' service"
	@echo "  make nuke             - stop, remove, volumes (irreversible)"

up:
	@if [ ! -f "$(INFRA)" ]; then echo "Missing $(INFRA)"; exit 1; fi
	docker compose -f $(INFRA) --env-file $(ENV) up -d --build

down:
	@if [ ! -f "$(INFRA)" ]; then echo "Missing $(INFRA)"; exit 1; fi
	docker compose -f $(INFRA) down --remove-orphans

logs:
	@if [ ! -f "$(INFRA)" ]; then echo "Missing $(INFRA)"; exit 1; fi
	docker compose -f $(INFRA) logs -f

ps:
	@if [ ! -f "$(INFRA)" ]; then echo "Missing $(INFRA)"; exit 1; fi
	docker compose -f $(INFRA) ps

rebuild-frontend:
	@if [ ! -f "$(INFRA)" ]; then echo "Missing $(INFRA)"; exit 1; fi
	docker compose -f $(INFRA) --env-file $(ENV) up -d --build frontend

# optional: bring the hammer
nuke:
	@if [ ! -f "$(INFRA)" ]; then echo "Missing $(INFRA)"; exit 1; fi
	docker compose -f $(INFRA) down --remove-orphans --volumes

smoke:
	curl -fsS http://localhost:8000/health >/dev/null
	curl -fsS http://localhost:3000/health >/dev/null
	@echo "smoke: ok"

rebuild:
	docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build

.PHONY: smoke
smoke:
	@set -e; \
	curl -fsS --retry 12 --retry-all-errors --retry-delay 1 http://localhost:8000/health >/dev/null; \
	curl -fsS --retry 12 --retry-all-errors --retry-delay 1 http://localhost:3000/health >/dev/null; \
	echo "smoke: ok"
