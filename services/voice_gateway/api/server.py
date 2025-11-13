"""FastAPI control surface for the voice gateway."""
from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="FrostGate Voice Gateway", version="0.1.0")


class VoiceSpec(BaseModel):
    secure: bool = Field(default=True)
    dscp: int = Field(..., description="DSCP to mark packets with")
    codec: str = Field(..., description="Codec selection")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Dict[str, int]:
    return {"voice_gateway_up": 1}


@app.post("/provision")
async def provision(spec: VoiceSpec) -> Dict[str, str]:
    if spec.dscp != 46:
        raise HTTPException(status_code=400, detail="DSCP must be EF (46)")
    return {"result": "accepted", "codec": spec.codec}
