import os
from typing import Dict

from fastapi import FastAPI, Request, HTTPException

from common.logging import log_event

VERSION = "0.1.0"

app = FastAPI(title="Sentinel Core")

def _auth(request: Request) -> None:
    token = request.headers.get("Authorization", "")
    if token != f"Bearer {os.environ.get('AUTH_TOKEN')}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/version")
async def version() -> Dict[str, str]:
    return {"version": VERSION}

@app.post("/analyze")
async def analyze(data: Dict[str, str], request: Request) -> Dict[str, str]:
    _auth(request)
    log_event("sentinelcore", "analyze called")
    return {"result": "neutral"}
