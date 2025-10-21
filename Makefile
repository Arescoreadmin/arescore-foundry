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

ps:
	$(COMPOSE) ps

rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d --wait

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

# sanity check to help humans find accidental duplicate targets
check:
	@printf "Scanning Makefile for duplicate target names...\n"; \
	awk -F':' '/^[a-zA-Z0-9_.-]+:/{print $$1}' Makefile \
	| sort | uniq -d | { read dups || exit 0; \
	if [ -n "$$dups" ]; then echo "Duplicate targets found:"; echo "$$dups"; exit 2; fi; }

env-core:
\t@docker exec -it sentinelcore env | grep -E 'RAG_CACHE|RAG_QUERY_TTL'

smoke-rag:
\t@docker exec -it sentinelcore python scripts/smoke_rag_cache.py || true

bench-rag:
\t@docker exec -i sentinelcore python - <<'PY'\nimport os,time\nos.environ.setdefault('RAG_CACHE_URL','sqlite:///data/rag_cache.sqlite3')\nfrom sentinelcore.rag_cache import Cache\nc=Cache();\nfrom time import perf_counter\ncalls={'e':0}\n\ndef slow(t):\n time.sleep(0.25); calls['e']+=1; return [float(len(t))]\ntext='x '*500\ns=perf_counter(); c.cached_embed(slow,text); m=perf_counter(); c.cached_embed(slow,text); e=perf_counter()\nprint('embed_calls=',calls['e'],' first_ms=',round((m-s)*1000,1),' second_ms=',round((e-m)*1000,1))\nPY

env-core:
\t@docker exec -it sentinelcore env | grep -E 'RAG_CACHE|RAG_QUERY_TTL' || true

rag-hits:
\t@CID=$$(python - <<'PY'\nimport uuid; print(uuid.uuid4())\nPY\n); \
\tcurl -s -H "X-Correlation-ID: $$CID" "http://localhost:8000/healthz" >/dev/null || true; \
\tcurl -s -H "X-Correlation-ID: $$CID" "http://localhost:8000/healthz" >/dev/null || true; \
\tdocker logs sentinelcore --since=5m | grep $$CID | grep -E "RAGCACHE (embed|ingest|query)" || true
