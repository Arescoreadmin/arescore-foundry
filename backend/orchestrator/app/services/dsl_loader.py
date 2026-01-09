from pathlib import Path
from typing import Any

# TODO: later wire this to config instead of hardcoding
SCENARIO_ROOT = Path("/app/scenario_dsl")

def load_topology(ref: str) -> dict[str, Any]:
    """
    MVP stub: load a topology definition by reference.
    Later: read YAML and validate against the DSL schema.
    """
    raise NotImplementedError("Topology loader not implemented yet")

def load_lesson(ref: str) -> dict[str, Any]:
    """
    MVP stub: load a lesson manifest by reference.
    """
    raise NotImplementedError("Lesson loader not implemented yet")
