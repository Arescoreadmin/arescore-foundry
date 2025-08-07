import hashlib
import json
import os
import threading
from typing import Dict

from fastapi import FastAPI, HTTPException, Request

VERSION = "0.1.0"

app = FastAPI(title="Log Indexer")

LOG_FILE = "/data/logs.json"
lock = threading.Lock()
logs = []
last_hash = "0"

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)
        if logs:
            last_hash = logs[-1].get("hash", "0")

def _save() -> None:
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f)

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

@app.post("/log")
async def log(entry: Dict[str, str], request: Request) -> Dict[str, str]:
    global last_hash
    _auth(request)
    message = entry.get("message", "")
    prev = last_hash
    hash_value = hashlib.sha256((prev + message).encode()).hexdigest()
    record = {"service": entry.get("service"), "message": message, "hash": hash_value}
    with lock:
        logs.append(record)
        last_hash = hash_value
        _save()
    return {"status": "logged"}

@app.get("/export")
async def export(request: Request) -> Dict[str, list]:
    _auth(request)
    return {"logs": logs}
