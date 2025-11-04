from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uuid

import httpx
import yaml

app = FastAPI(title="spawn_service")


class SpawnRequest(BaseModel):
    track: str


class SpawnResponse(BaseModel):
    scenario_id: str
    access_url: Optional[str] = None


TEMPLATE_PATHS: Dict[str, str] = {
    "netplus": "/templates/netplus.yaml",
    "ccna": "/templates/ccna.yaml",
    "cissp": "/templates/cissp.yaml",
}

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8080")
ORCHESTRATOR_SCENARIOS_PATH = "/api/scenarios"


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    return {"status": "ready"}


@app.post("/api/spawn", response_model=SpawnResponse)
async def spawn(req: SpawnRequest) -> SpawnResponse:
    track = req.track.lower()
    if track not in TEMPLATE_PATHS:
        raise HTTPException(status_code=400, detail=f"Unsupported track: {track}")

    template_path = TEMPLATE_PATHS[track]

    # Load scenario template
    try:
        with open(template_path, "r") as f:
            scenario: Dict[str, Any] = yaml.safe_load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Template not found: {template_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load template: {e}")

    # Assign a name/id into metadata if present
    scenario_id = str(uuid.uuid4())
    metadata = scenario.get("metadata") or {}
    metadata["name"] = f"{track}-{scenario_id}"
    scenario["metadata"] = metadata

    url = f"{ORCHESTRATOR_URL}{ORCHESTRATOR_SCENARIOS_PATH}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=scenario)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Orchestrator unreachable: {e}")

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Orchestrator error {resp.status_code}: {resp.text[:200]}",
        )

    data = resp.json() if resp.content else {}
    orch_id = data.get("id") or data.get("scenario_id") or scenario_id

    access_url = f"https://mvp.local/console/{orch_id}"
    return SpawnResponse(scenario_id=orch_id, access_url=access_url)
