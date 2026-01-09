from typing import Literal

State = Literal["pending", "provisioning", "running", "completed", "failed"]

def load_state(session_id: str) -> dict:
    """
    MVP stub: load orchestrator state for a session.
    Backed by DB or in-memory store later.
    """
    raise NotImplementedError("State load not implemented yet")

def save_state(session_id: str, state: dict) -> None:
    """
    MVP stub: persist orchestrator state.
    """
    raise NotImplementedError("State save not implemented yet")

def transition(session_id: str, new_state: State) -> dict:
    """
    MVP stub: transition FSM and return updated state.
    """
    raise NotImplementedError("FSM transition not implemented yet")
