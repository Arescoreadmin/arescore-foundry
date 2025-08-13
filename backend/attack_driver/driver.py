import os
from fastapi import FastAPI

app = FastAPI(title="Attack Driver", version="0.1")

@app.post('/run')
async def run(mode: str = 'recon'):
    # Placeholder: integrate SentinelRed playbooks here
    return {"mode": mode, "status": "started"}
@app.get("/health")
async def health():
    return {"ok": True}
