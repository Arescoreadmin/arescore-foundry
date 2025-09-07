from fastapi import FastAPI
import os, httpx

LOGS = os.getenv("LOG_INDEXER_URL", "http://log_indexer:8081")
ORCH = os.getenv("ORCH_URL", "http://orchestrator:8000")
OBSV = os.getenv("OBSERVER_URL", "http://observer_hub:8070")

app = FastAPI(title="RCA AI", version="0.1")

@app.post("/diagnose")
async def diagnose():
    # Minimal heuristic RCA: fetch alerts + recent logs and return suggested fix
    async with httpx.AsyncClient(timeout=8) as c:
        alerts = (await c.get(f"{OBSV}/risks")).json()
        # In real impl, pull log window from log_indexer and run model
    suggestion = {
        "likely_cause": "Nginx header misconfig causing 502s",
        "fix_steps": ["Run scripts/patch_frontend_nginx.sh", "Restart frontend"],
        "script": "scripts/patch_frontend_nginx.sh"
    }
    return {"alerts": alerts, "suggestion": suggestion}
@app.get("/health")
async def health():
    return {"ok": True}
