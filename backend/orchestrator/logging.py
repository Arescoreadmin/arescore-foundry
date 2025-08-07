import os
from typing import Any, Dict

import requests

LOG_INDEXER_URL = os.environ.get("LOG_INDEXER_URL")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")


def log_event(service: str, message: str, extra: Dict[str, Any] | None = None) -> None:
    """Send a log event to the central log indexer."""
    if not LOG_INDEXER_URL or not AUTH_TOKEN:
        return
    payload = {"service": service, "message": message}
    if extra:
        payload.update(extra)
    try:
        requests.post(
            f"{LOG_INDEXER_URL}/log",
            json=payload,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5,
        )
    except Exception:
        pass
