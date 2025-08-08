from fastapi import FastAPI, Body
import hashlib
from datetime import datetime
from typing import List

app = FastAPI(title="Log Indexer")

logs: List[dict] = []

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/log")
def add_log(message: str = Body(..., embed=True)) -> dict:
    timestamp = datetime.utcnow().isoformat()
    digest = hashlib.sha256(message.encode()).hexdigest()
    entry = {"timestamp": timestamp, "hash": digest, "message": message}
    logs.append(entry)
    return entry

@app.get("/logs")
def get_logs() -> List[dict]:
    return logs
