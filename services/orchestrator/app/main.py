from __future__ import annotations

import functools
import hashlib
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Iterable

from fastapi import FastAPI, HTTPException
from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from arescore_foundry_lib.policy import (
    AuditLogger,
    OPAClient,
    PolicyBundle,
    PolicyError,
)

from .telemetry import emit_event


class Settings(BaseSettings):
    """Configuration for orchestrator policy management."""

    model_config = SettingsConfigDict(
        env_prefix="FOUNDRY_ORCHESTRATOR_",
        case_sensitive=False,
    )

    opa_url: str = Field(default="http://opa:8181", alias="OPA_URL")
    opa_policy_prefix: str | None = Field(default="foundry", alias="OPA_POLICY_PREFIX")
    opa_timeout: float = Field(default=5.0, alias="OPA_TIMEOUT")
    policy_directories: tuple[str, ...] = Field(
        default=("policies", "_container_policies"),
        alias="POLICY_DIRECTORIES",
    )
    policy_audit_log: Path = Field(
        default=Path("audits") / "orchestrator-policy-sync.jsonl",
        alias="POLICY_AUDIT_LOG",
    )

    @field_validator("policy_directories", mode="before")
    @classmethod
    def _split_policy_directories(
        cls, value: Any, info: ValidationInfo
    ) -> tuple[str, ...]:
        if value is None:
            default = info.field.default
            if isinstance(default, (list, tuple)):
                return tuple(default)
            if default is None:
                return ()
            return (str(default),)
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
            return tuple(part for part in parts if part)
        if isinstance(value, (list, tuple)):
            return tuple(str(part).strip() for part in value if str(part).strip())
        return tuple(value)

@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()


@functools.lru_cache()
def get_policy_audit_logger() -> AuditLogger:
    return AuditLogger(get_settings().policy_audit_log)


def _normalise_directories(directories: Iterable[str]) -> tuple[str, ...]:
    normalised: list[str] = []
    for directory in directories:
        directory = str(directory).strip()
        if directory:
            normalised.append(directory)
    return tuple(normalised)


def load_policy_bundle() -> PolicyBundle:
    """Load the orchestrator policy bundle from the configured directories."""

    settings = get_settings()
    directories = _normalise_directories(settings.policy_directories)
    return PolicyBundle.from_directories(*directories)


def create_opa_client() -> OPAClient | None:
    """Return an OPA client when a base URL is configured."""

    settings = get_settings()
    if not settings.opa_url:
        return None
    return OPAClient(settings.opa_url, timeout=settings.opa_timeout)


def _bundle_snapshot_id(bundle: PolicyBundle) -> str:
    digest = hashlib.sha256(bundle.to_json(indent=None).encode("utf-8")).hexdigest()
    return digest[:16]


def synchronise_policy_bundle() -> None:
    """Synchronise local Rego policies with the shared OPA instance."""

    logger = get_policy_audit_logger()
    try:
        bundle = load_policy_bundle()
    except PolicyError as exc:
        logger.log(
            service="orchestrator",
            snapshot_id=None,
            status="error",
            details={"error": str(exc)},
        )
        raise

    snapshot_id = _bundle_snapshot_id(bundle)
    client = create_opa_client()

    if client is None:
        logger.log(
            service="orchestrator",
            snapshot_id=snapshot_id,
            status="skipped",
            details={
                "reason": "OPA client not configured",
                "module_count": len(bundle.modules),
            },
        )
        return

    settings = get_settings()

    try:
        client.publish_bundle(bundle, prefix=settings.opa_policy_prefix)
    except PolicyError as exc:
        logger.log(
            service="orchestrator",
            snapshot_id=snapshot_id,
            status="error",
            details={"error": str(exc)},
        )
        raise

    logger.log(
        service="orchestrator",
        snapshot_id=snapshot_id,
        status="published",
        details={
            "module_count": len(bundle.modules),
            "prefix": settings.opa_policy_prefix or "",
        },
    )


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    synchronise_policy_bundle()
    yield


app = FastAPI(title="orchestrator", lifespan=_lifespan)


# In-memory store for MVP; replace with real controller later
SCENARIOS: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    # future: check OPA, NATS, workers, etc.
    return {"status": "ready"}


@app.post("/api/scenarios")
def create_scenario(scenario: Dict[str, Any]) -> dict:
    """
    Minimal MVP endpoint:
      - Accepts arbitrary JSON as the scenario payload.
      - Assigns a UUID.
      - Stores it in memory.
      - Returns the id.
    Later you:
      - validate against the scenario DSL
      - call OPA
      - spin containers
      - emit NATS events
    """
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
