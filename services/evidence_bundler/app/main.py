from fastapi import FastAPI
from pydantic import BaseModel
import uuid
app = FastAPI()
@app.get("/health")
def health(): return {"ok": True}
class Evidence(BaseModel):
    run_id: str | None = None
    notes: str | None = None
@app.post("/evidence")
def add_evidence(ev: Evidence):
    return {"evidence_id": str(uuid.uuid4()), "received": ev.model_dump()}
