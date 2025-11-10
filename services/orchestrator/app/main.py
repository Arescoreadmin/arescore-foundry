import logging
import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from services.common.telemetry import TelemetryPublisher

app = FastAPI(title="orchestrator")
telemetry_publisher = TelemetryPublisher()
logger = logging.getLogger(__name__)


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


@app.on_event("startup")
async def startup() -> None:
    try:
        await telemetry_publisher.connect()
    except Exception as exc:
        logger.warning(
            "Telemetry publisher unavailable during startup; continuing without NATS: %s",
            exc,
        )


@app.on_event("shutdown")
async def shutdown() -> None:
    await telemetry_publisher.close()


@app.post("/api/scenarios")
async def create_scenario(scenario: Dict[str, Any]) -> dict:
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

    await telemetry_publisher.publish(
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
