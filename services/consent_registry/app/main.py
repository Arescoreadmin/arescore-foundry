from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()
@app.get("/health")
def health(): return {"ok": True}
class OptIn(BaseModel):
    subject_id: str | None = None
    model_hash: str | None = None
@app.post("/consent/training/optin")
def optin(payload: OptIn | None = None):
    return {"status":"opted_in","subject": (payload.subject_id if payload else None)}
@app.get("/crl")
def crl(): return {"serials": []}
