# ===== AresCore Foundry — Makefile (production-ready) =====

# --- Tunables (override via env or make VAR=...) ---
ENV_FILE        ?= /etc/arescore-foundry.env
BASE            ?= /opt/arescore-foundry

# OPA pinned (1.10.0 digest you verified)
OPA_IMG         := openpolicyagent/opa@sha256:c0814ce7811ecef8f1297a8e55774a1d5422e5c18b996b665acbc126124fab19

# Compose overlays (set USE_FEDERATED=1, PROD_USE_STAGING=1 as needed)
USE_FEDERATED    ?= 0
PROD_USE_STAGING ?= 0
USE_TELEMETRY    ?= 0

# Paths
POL_DIR         := $(PWD)/policies

# Compose builder
COMPOSE_FILES   := -f compose.yml
ifeq ($(USE_FEDERATED),1)
COMPOSE_FILES   += -f compose.federated.yml
endif
ifeq ($(PROD_USE_STAGING),1)
COMPOSE_FILES   += -f compose.staging.yml
endif
ifeq ($(USE_TELEMETRY),1)
COMPOSE_FILES   += -f compose.telemetry.yml
endif
COMPOSE         := docker compose --env-file $(ENV_FILE) $(COMPOSE_FILES)

# Default goal
.DEFAULT_GOAL := help

# ----- Helpers -----
define _header
	@printf '\n\033[1;36m==> %s\033[0m\n' "$(1)"
endef

# ===== Targets =====
.PHONY: help
help:
	@echo "AresCore Foundry — common targets"
@echo "  make up                 # start stack (add USE_FEDERATED=1, PROD_USE_STAGING=1, USE_TELEMETRY=1)"
	@echo "  make down               # stop stack + remove orphans"
	@echo "  make build              # build images (honors overlays)"
	@echo "  make rebuild            # build --no-cache and start"
	@echo "  make restart            # restart core services"
	@echo "  make ps                 # show services"
	@echo "  make logs               # tail key logs"
	@echo "  make opa-check          # static check policies"
	@echo "  make opa-test           # run OPA unit tests"
	@echo "  make opa-eval           # sample eval against policies"
	@echo "  make smoke              # overlay smoke (ensures up + hits endpoints)"
	@echo "  make fix                # run foundry_autofix.sh (root required)"
	@echo "  make release            # run scripts/prod_release_v2.sh"
	@echo "  make up-overlay         # alias for USE_FEDERATED=1 make up"

# ----- OPA -----
.PHONY: opa-check
opa-check:
	$(call _header,OPA check)
	@docker run --rm -v "$(POL_DIR):/policies:ro" $(OPA_IMG) check /policies

.PHONY: opa-test
opa-test:
	$(call _header,OPA unit tests)
	@docker run --rm -v "$(POL_DIR):/policies:ro" $(OPA_IMG) test -v /policies

.PHONY: opa-eval
opa-eval:
	$(call _header,OPA eval sample)
	@printf '%s' '{"input":{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}}' \
	| docker run --rm -i -v "$(POL_DIR):/policies:ro" $(OPA_IMG) eval -f pretty -d /policies 'data.foundry.training.allow'

# ----- Compose lifecycle -----
.PHONY: build
build:
	$(call _header,Build images)
	@$(COMPOSE) build

.PHONY: rebuild
rebuild:
	$(call _header,Rebuild images (no cache) + up)
	@$(COMPOSE) build --no-cache
	@$(COMPOSE) up -d --remove-orphans

.PHONY: up
up:
	$(call _header,Starting stack)
	@$(COMPOSE) up -d --remove-orphans

.PHONY: down
down:
	$(call _header,Stopping stack)
	@docker compose --env-file $(ENV_FILE) -f $(BASE)/compose.yml -f $(BASE)/compose.override.yml down || true

.PHONY: restart
restart:
	$(call _header,Restarting core services)
	@$(COMPOSE) restart opa orchestrator || true

.PHONY: ps
ps:
	$(call _header,Compose services)
	@$(COMPOSE) ps

# ----- Logs -----
.PHONY: logs
logs:
	$(call _header,Recent logs)
	@docker logs --tail=200 arescore-foundry-opa-1 || true
	@docker logs --tail=200 arescore-foundry-orchestrator-1 || true
	@docker logs --tail=200 arescore-foundry-fl_coordinator-1 || true
	@docker logs --tail=200 arescore-foundry-consent_registry-1 || true
	@docker logs --tail=200 arescore-foundry-evidence_bundler-1 || true
	@docker logs --tail=200 arescore-foundry-spawn_service-1 || true

# ----PHO- Smokes & maintenance -----
.PHONY: smoke
smoke: up
	$(call _header,Overlay smoke)
	@bash ./scripts/smoke_overlay.sh

.PHONY: fix
fix:
	$(call _header,Auto-fix compose + OPA wiring)
	@sudo -E BASE=$(BASE) ENV_FILE=$(ENV_FILE) bash scripts/foundry_autofix.sh


.PHONY: release
release:
	@bash scripts/prod_release_final.sh

.PHONY: overlay-smoke
overlay-smoke:
	bash ./scripts/smoke_overlay.sh

.PHONY: sbom
sbom:
	@PROJECT_NAME=arescore-foundry \
	 COMPOSE_FILES="-f compose.yml -f compose.federated.yml" \
	 ARTIFACT_DIR="artifacts" \
	 bash scripts/report_sbom.sh && echo "SBOMs ready in artifacts/"

.PHONY: release sbom
release:
	@bash scripts/prod_release_final.sh

sbom:
	@ARTIFACT_DIR="artifacts" COMPOSE_FILES="-f compose.yml -f compose.federated.yml" bash scripts/report_sbom.sh && echo "SBOMs in ./artifacts"
