from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable, Dict, List

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

UTC = timezone.utc
STALE_THRESHOLD_SECONDS = 300


class RevocationEntry(BaseModel):
    runtime_id: str
    reason: str | None = None
    issued_at: datetime
    expires_at: datetime | None = None

    def is_active(self, now: datetime) -> bool:
        return self.expires_at is None or self.expires_at > now


class RevocationSnapshot(BaseModel):
    runtime_ids: List[str]
    entries: List[RevocationEntry]
    last_updated: datetime | None = None
    stale: bool = False


class RevokeRequest(BaseModel):
    runtime_id: str = Field(..., min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=512)
    ttl_seconds: int | None = Field(default=None, ge=1, le=86_400)

    @field_validator("runtime_id")
    @classmethod
    def _strip_runtime_id(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("runtime_id must not be blank")
        return trimmed

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class RevocationRegistry:
    """In-memory registry of revoked runtime identifiers."""

    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self._now: Callable[[], datetime] = now or (lambda: datetime.now(tz=UTC))
        self._entries: Dict[str, RevocationEntry] = {}
        self._lock = Lock()
        self._last_update: datetime | None = None

    def set_time_provider(self, provider: Callable[[], datetime]) -> None:
        """Swap the time provider used by the registry (primarily for tests)."""
        self._now = provider

    def revoke(self, request: RevokeRequest) -> RevocationEntry:
        issued_at = self._now()
        expires_at = (
            issued_at + timedelta(seconds=request.ttl_seconds)
            if request.ttl_seconds is not None
            else None
        )
        entry = RevocationEntry(
            runtime_id=request.runtime_id,
            reason=request.reason,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        with self._lock:
            self._entries[entry.runtime_id] = entry
            self._last_update = issued_at
        return entry

    def reinstate(self, runtime_id: str) -> bool:
        with self._lock:
            removed = self._entries.pop(runtime_id, None) is not None
            if removed:
                self._last_update = self._now()
            return removed

    def _prune_expired(self, now: datetime) -> None:
        expired = [rid for rid, entry in self._entries.items() if not entry.is_active(now)]
        for rid in expired:
            self._entries.pop(rid, None)

    def snapshot(self) -> RevocationSnapshot:
        now = self._now()
        with self._lock:
            self._prune_expired(now)
            entries = list(self._entries.values())
            last_update = self._last_update
        stale = False
        if last_update is None:
            stale = True
        else:
            stale = (now - last_update).total_seconds() > STALE_THRESHOLD_SECONDS
        runtime_ids = sorted(entry.runtime_id for entry in entries)
        return RevocationSnapshot(
            runtime_ids=runtime_ids,
            entries=entries,
            last_updated=last_update,
            stale=stale,
        )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._last_update = self._now()


app = FastAPI(title="runtime_revocation_service")
registry = RevocationRegistry()


@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/live")
def live() -> Dict[str, str]:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> Dict[str, str]:
    snapshot = registry.snapshot()
    status_str = "degraded" if snapshot.stale else "ready"
    return {"status": status_str}


@app.get("/revocations/runtime", response_model=RevocationSnapshot)
def list_runtime_revocations() -> RevocationSnapshot:
    return registry.snapshot()


@app.post(
    "/revocations/runtime",
    response_model=RevocationEntry,
    status_code=status.HTTP_201_CREATED,
)
def revoke_runtime(request: RevokeRequest) -> RevocationEntry:
    return registry.revoke(request)


@app.delete("/revocations/runtime/{runtime_id}")
def reinstate_runtime(runtime_id: str) -> Dict[str, bool]:
    trimmed = runtime_id.strip()
    if not trimmed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "runtime_id must not be blank")
    removed = registry.reinstate(trimmed)
    return {"removed": removed}
