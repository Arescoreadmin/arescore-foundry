import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from .telemetry import emit_event

app = FastAPI(title="orchestrator")


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
