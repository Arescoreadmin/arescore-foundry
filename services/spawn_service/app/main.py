from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from arescore_foundry_lib.policy import (
    AuditLogger,
    OpaClient,
    OpaDecisionDenied,
    PolicyBundle,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Service responsible for orchestrating tenant-scoped scenario spawns.",
)

class SpawnRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    track: str
    dataset_id: Optional[str] = None
    model_hash: Optional[str] = None
    consent_signature: Optional[str] = None

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)



_TEMPLATE_SEARCH_PATHS = []
_template_env = os.getenv("SCENARIO_TEMPLATE_DIR")
if _template_env:
    _TEMPLATE_SEARCH_PATHS.append(Path(_template_env))
_TEMPLATE_SEARCH_PATHS.append(Path("/templates"))
_TEMPLATE_SEARCH_PATHS.append(Path(__file__).resolve().parents[3] / "templates")

TEMPLATE_TRACKS = {"netplus", "ccna", "cissp"}

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8080")
ORCHESTRATOR_SCENARIOS_PATH = "/api/scenarios"

_ROOT = Path(__file__).resolve().parents[3]
_POLICY_DIR = Path(os.getenv("POLICY_DIR", _ROOT / "policies"))
_POLICY_BUNDLE = PolicyBundle.from_directory(_POLICY_DIR)
_AUDIT_LOGGER = AuditLogger.from_env(service="spawn_service", default_directory=_ROOT / "audits")
OPA_CLIENT = OpaClient(bundle=_POLICY_BUNDLE, audit_logger=_AUDIT_LOGGER)


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
    if track not in TEMPLATE_TRACKS:
        raise HTTPException(status_code=400, detail=f"Unsupported track: {track}")

    template_path = _resolve_template_path(track)

    # Load scenario template
    try:
        with template_path.open("r", encoding="utf-8") as f:
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

    policy_input = {
        "track": track,
        "dataset": {"id": req.dataset_id or ""},
        "model": {"hash": req.model_hash or ""},
        "tokens": {"consent": {"signature": req.consent_signature or ""}},
    }

    try:
        await OPA_CLIENT.ensure_allow_async("foundry/training_gate", policy_input)
    except OpaDecisionDenied as exc:
        raise HTTPException(status_code=403, detail=f"spawn denied: {exc.reason or 'policy rejection'}") from exc

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


def _resolve_template_path(track: str) -> Path:
    for base in _TEMPLATE_SEARCH_PATHS:
        if base is None:
            continue
        candidate = base / f"{track}.yaml"
        if candidate.exists():
            return candidate
    # Last resort: assume /templates even if not present so error message matches original behaviour
    return Path("/templates") / f"{track}.yaml"
