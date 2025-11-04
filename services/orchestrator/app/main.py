from fastapi import FastAPI, HTTPException
from typing import Any, Dict
import uuid

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
    return {"id": scenario_id}


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> Dict[str, Any]:
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"id": scenario_id, "payload": SCENARIOS[scenario_id]}
