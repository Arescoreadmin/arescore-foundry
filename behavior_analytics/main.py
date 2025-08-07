import requests
from fastapi import FastAPI

from .config import get_settings
from .models import Event

app = FastAPI(title="Behavior Analytics")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def _log(message: str) -> None:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}
    try:
        requests.post(
            f"{settings.log_indexer_url}/log",
            json={"service": "behavior_analytics", "message": message},
            headers=headers,
            timeout=5,
        )
    except Exception:
        pass


def _alert(detail: str) -> None:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}
    try:
        requests.post(f"{settings.orchestrator_url}/alerts", json={"detail": detail}, headers=headers)
    except Exception:
        pass


@app.post("/events")
async def handle_event(event: Event) -> dict:
    settings = get_settings()
    _log(f"event received: {event.value}")
    if event.value > settings.anomaly_threshold:
        _log(f"anomaly detected: {event.value}")
        _alert(f"anomaly: {event.value}")
        return {"status": "anomaly"}
    return {"status": "ok"}
