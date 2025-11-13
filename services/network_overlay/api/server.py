"""FastAPI control surface for the FrostGate network overlay service."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

app = FastAPI(title="FrostGate Network Overlay", version="0.1.0")


class OverlaySpec(BaseModel):
    type: str = Field(..., description="Overlay technology, e.g. vxlan")
    vni: int | None = Field(None, description="VXLAN Network Identifier")
    mtu: int = Field(..., ge=1200, description="Desired MTU for overlay path")
    ports: List[int] = Field(default_factory=list, description="UDP/TCP ports in use")
    endpoints: List[str] = Field(default_factory=list, description="Overlay endpoints")

    @validator("type")
    def normalize_type(cls, value: str) -> str:
        return value.lower()

    @validator("vni")
    def validate_vni(cls, value: int | None, values: Dict[str, Any]) -> int | None:
        overlay_type = values.get("type")
        if overlay_type == "vxlan" and value is None:
            raise ValueError("VXLAN overlays require a VNI")
        return value


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Dict[str, int]:
    return {"overlay_up": 1}


@app.post("/create")
async def create_overlay(spec: OverlaySpec) -> Dict[str, Any]:
    if spec.mtu < 1500:
        raise HTTPException(status_code=400, detail="MTU too small for overlay")
    return {
        "result": "accepted",
        "overlay": spec.dict(),
    }


@app.post("/delete")
async def delete_overlay(spec: OverlaySpec) -> Dict[str, Any]:
    return {"result": "deleted", "overlay": spec.dict()}
