## Acceptance criteria
- [ ] `docker compose up -d --build` starts **frontend**, **orchestrator**, **log_indexer** as **healthy**.
- [ ] `GET /ready` on frontend returns `{"ready":true}`.
- [ ] `GET /api/ready` via frontend returns orchestrator JSON.
- [ ] Orchestrator `/health` returns `{"status":"ok"}`.
- [ ] Frontend runs as non-root at runtime.

## Risks / mitigations
- Healthcheck flakiness → retries configured; curl installed in runtime.
- Port conflicts → override in compose env if needed.

## Rollback
`git revert` this PR or `docker compose down && git checkout <prev tag>`.
