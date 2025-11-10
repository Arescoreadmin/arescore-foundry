from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from arescore_foundry_lib.policy import (
    AuditLogger,
    OpaClient,
    OpaDecisionDenied,
    PolicyBundle,
)

from .telemetry import emit_event

app = FastAPI(title="orchestrator")


# In-memory store for MVP; replace with real controller later
SCENARIOS: Dict[str, Dict[str, Any]] = {}

_ROOT = Path(__file__).resolve().parents[3]
_POLICY_DIR = Path(os.getenv("POLICY_DIR", _ROOT / "policies"))
_POLICY_BUNDLE = PolicyBundle.from_directory(_POLICY_DIR)
_AUDIT_LOGGER = AuditLogger.from_env(service="orchestrator", default_directory=_ROOT / "audits")
OPA_CLIENT = OpaClient(bundle=_POLICY_BUNDLE, audit_logger=_AUDIT_LOGGER)
_CRL_SERIALS = [s.strip() for s in os.getenv("CRL_SERIALS", "").split(",") if s.strip()]


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    # future: check OPA, NATS, workers, etc.
    return {"status": "ready", "policy_version": OPA_CLIENT.version}


@app.get("/api/policies/bundle")
def policy_bundle() -> JSONResponse:
    return JSONResponse(
        {
            "version": _POLICY_BUNDLE.version,
            "packages": list(_POLICY_BUNDLE.packages),
            "bundle": _POLICY_BUNDLE.to_base64(),
            "manifest": _POLICY_BUNDLE.manifest(),
        }
    )


@app.post("/api/scenarios")
def create_scenario(scenario: Dict[str, Any]) -> dict:
    """Register a scenario after validating policy gates."""

    if not isinstance(scenario, dict):
        raise HTTPException(status_code=400, detail="Scenario must be an object")

    try:
        OPA_CLIENT.ensure_allow(
            "foundry/authority",
            {"auth": scenario.get("auth", {}), "crl": {"serials": _CRL_SERIALS}},
        )
        OPA_CLIENT.ensure_allow(
            "foundry/consent", {"tokens": scenario.get("tokens", {})}
        )
    except OpaDecisionDenied as exc:
        raise HTTPException(status_code=403, detail=f"scenario denied: {exc.reason or 'policy rejection'}") from exc

    scenario_id = str(uuid.uuid4())
    SCENARIOS[scenario_id] = scenario

    name: str = ""
    template: str = ""
    description: str = ""

    if isinstance(scenario, dict):
        name = str(scenario.get("name", ""))
        template = str(scenario.get("template", ""))
        description = str(scenario.get("description", ""))
    else:
        name = getattr(scenario, "name", "")
        template = getattr(scenario, "template", "")
        description = getattr(scenario, "description", "")

    emit_event(
        "scenario.created",
        {
            "scenario_id": scenario_id,
            "name": name,
            "template": template,
            "description": description,
        },
    )

    return {"id": scenario_id}


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> Dict[str, Any]:
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"id": scenario_id, "payload": SCENARIOS[scenario_id]}
