import os
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from common.logging import log_event

VERSION = "0.1.0"

app = FastAPI(title="Orchestrator")

worlds: Dict[int, str] = {}
next_id = 1

def _auth(request: Request) -> None:
    token = request.headers.get("Authorization", "")
    if token != f"Bearer {os.environ.get('AUTH_TOKEN')}":
        raise HTTPException(status_code=401, detail="Unauthorized")

class World(BaseModel):
    name: str

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/version")
async def version() -> Dict[str, str]:
    return {"version": VERSION}

@app.get("/worlds")
async def list_worlds(request: Request) -> Dict[str, List[str]]:
    _auth(request)
    return {"worlds": list(worlds.values())}

@app.post("/worlds")
async def create_world(world: World, request: Request) -> Dict[str, str]:
    global next_id
    _auth(request)
    world_id = next_id
    next_id += 1
    worlds[world_id] = world.name
    log_event("orchestrator", f"world created: {world.name}")
    return {"id": world_id, "name": world.name}

@app.delete("/worlds/{world_id}")
async def delete_world(world_id: int, request: Request) -> Dict[str, str]:
    _auth(request)
    name = worlds.pop(world_id, None)
    if name is None:
        raise HTTPException(status_code=404, detail="World not found")
    log_event("orchestrator", f"world deleted: {name}")
    return {"status": "deleted"}
