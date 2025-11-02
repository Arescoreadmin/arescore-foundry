OPA_IMG := openpolicyagent/opa:0.67.0@sha256:3b59c5dd0e6f7f9a5a31f7af64b2b1f1a5d7e141b9f0d2a8f9d2f0c1a6b9e7c3
POL_DIR := $(PWD)/policies
COMPOSE := docker compose --env-file /etc/arescore-foundry.env -f compose.yml
BASE ?= /opt/arescore-foundry
ENV_FILE ?= /etc/arescore-foundry.env

.PHONY: opa-check opa-test opa-eval up down restart smoke

opa-check:
	@docker run --rm -v "$(POL_DIR):/policies:ro" $(OPA_IMG) check /policies

opa-test:
	@docker run --rm -v "$(POL_DIR):/policies:ro" $(OPA_IMG) test -v /policies

opa-eval:
	@printf '%s' '{"input":{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}}' \
	| docker run --rm -i -v "$(POL_DIR):/policies:ro" $(OPA_IMG) eval -f pretty -d /policies 'data.foundry.training.allow'

up:
	@$(COMPOSE) up -d --remove-orphans

down:
	@docker compose --env-file $(ENV_FILE) -f $(BASE)/compose.yml -f $(BASE)/compose.override.yml down || true

restart:
	@$(COMPOSE) restart opa orchestrator

fix:
	@sudo -E BASE=$(BASE) ENV_FILE=$(ENV_FILE) bash scripts/foundry_autofix.sh

logs:
	@docker logs --tail=200 arescore-foundry-opa-1 || true
	@docker logs --tail=200 arescore-foundry-orchestrator-1 || true

opa-test:
	docker run --rm -v "$(PWD)/policies":/policies:ro openpolicyagent/opa:1.10.0 test /policies -v

.PHONY: smoke
smoke:
	bash ./scripts/smoke_overlay.sh
