from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI

from .config import settings
from .crl import CRLParseError, RevocationSnapshot, crl_fingerprint, extract_revocations

logger = logging.getLogger("revocation_service")
logging.basicConfig(level=logging.INFO)


class ServiceState:
    def __init__(self) -> None:
        self.snapshot: Optional[RevocationSnapshot] = None
        self.last_fetch: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.fingerprint: Optional[str] = None

    def as_health(self) -> dict:
        return {
            "crl_url": settings.crl_url,
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch else None,
            "last_error": self.last_error,
            "runtime_count": len(self.snapshot.runtime_ids) if self.snapshot else 0,
        }

    def revocation_payload(self) -> dict:
        snapshot = self.snapshot
        return {
            "runtime_ids": snapshot.runtime_ids if snapshot else [],
            "this_update": snapshot.this_update.isoformat() if snapshot else None,
            "next_update": snapshot.next_update.isoformat() if snapshot and snapshot.next_update else None,
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch else None,
        }


state = ServiceState()
app = FastAPI(title="runtime-revocation-service")


async def _publish_to_opa(client: httpx.AsyncClient, snapshot: RevocationSnapshot) -> None:
    if not settings.opa_push_enabled:
        return

    url = f"{settings.opa_base_url.rstrip('/')}/v1/data/runtime_revocation_feed"
    payload = {"value": snapshot.as_dict()}
    response = await client.put(url, json=payload, timeout=5)
    response.raise_for_status()


async def _refresh_once(client: httpx.AsyncClient) -> None:
    if not settings.crl_url:
        state.last_error = "CRL_URL not configured"
        logger.warning("CRL_URL is unset; skipping fetch")
        return

    try:
        response = await client.get(settings.crl_url, timeout=10)
        response.raise_for_status()
        payload = response.content
        snapshot = extract_revocations(payload)

        state.snapshot = snapshot
        state.last_fetch = datetime.now(timezone.utc)
        state.fingerprint = crl_fingerprint(payload)
        state.last_error = None

        try:
            await _publish_to_opa(client, snapshot)
        except httpx.HTTPError as exc:
            state.last_error = f"OPA push failed: {exc}"
            logger.error("Failed to push revocations to OPA: %s", exc)

        logger.info(
            "Updated revocation cache with %s entries (this_update=%s)",
            len(snapshot.runtime_ids),
            snapshot.this_update.isoformat(),
        )
    except (httpx.HTTPError, CRLParseError) as exc:
        state.last_error = str(exc)
        logger.error("Failed to refresh revocation data: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive
        state.last_error = str(exc)
        logger.exception("Unexpected error while refreshing revocations")


async def _poller() -> None:
    interval = max(30, settings.crl_refresh_seconds)
    async with httpx.AsyncClient() as client:
        while True:
            await _refresh_once(client)
            await asyncio.sleep(interval)


@app.on_event("startup")
async def startup() -> None:
    app.state.poller = asyncio.create_task(_poller())


@app.on_event("shutdown")
async def shutdown() -> None:
    poller: asyncio.Task | None = getattr(app.state, "poller", None)
    if poller:
        poller.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poller


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", **state.as_health()}


@app.get("/revocations")
async def get_revocations() -> dict:
    return state.revocation_payload()


@app.post("/revocations/reload", status_code=202)
async def force_reload() -> dict:
    async with httpx.AsyncClient() as client:
        await _refresh_once(client)
    return {"status": "refresh-scheduled", "last_error": state.last_error}


@app.get("/opa/input")
async def opa_payload() -> dict:
    payload = state.revocation_payload()
    return {"revocation": {"runtime_ids": payload["runtime_ids"]}}
