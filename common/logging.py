"""Async HTTP log emitter."""
import asyncio
import os
from typing import Any, Dict

import httpx

LOG_ENDPOINT = os.getenv("LOG_ENDPOINT")
LOG_TOKEN = os.getenv("LOG_TOKEN", "changeme-dev")

async def _post(event: Dict[str, Any]) -> None:
    """Send a log event to the log indexer."""
    if not LOG_ENDPOINT:
        return
    headers = {"Authorization": f"Bearer {LOG_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=1) as client:
            await client.post(LOG_ENDPOINT, json=event, headers=headers)
    except Exception:
        # Non-blocking: swallow errors if indexer is down
        pass

def emit(event: Dict[str, Any]) -> None:
    """Fire-and-forget log emission."""
    asyncio.create_task(_post(event))
