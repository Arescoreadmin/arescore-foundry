from fastapi import FastAPI
import httpx

app = FastAPI(title="Orchestrator")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/start")
async def start_session() -> dict:
    """Placeholder endpoint to demonstrate interaction with other services."""
    async with httpx.AsyncClient() as client:
        core = await client.get("http://sentinel_core:8001/health")
        red = await client.get("http://sentinel_red:8002/health")
    return {"sentinel_core": core.json(), "sentinel_red": red.json()}
