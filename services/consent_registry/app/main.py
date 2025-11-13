from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(title="consent_registry")


@dataclass
class ConsentRecord:
    """In-memory representation of a training consent."""

    subject: str
    token: str
    metadata: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConsentRegistry:
    """Stores training opt-in state for the smoke tests."""

    def __init__(self) -> None:
        self._records: dict[str, ConsentRecord] = {}

    def opt_in(self, *, subject: str, token: str, metadata: dict[str, Any] | None) -> ConsentRecord:
        record = ConsentRecord(subject=subject, token=token, metadata=dict(metadata or {}))
        self._records[subject] = record
        return record

    def get(self, subject: str) -> ConsentRecord | None:
        return self._records.get(subject)

    def clear(self) -> None:
        self._records.clear()


@dataclass
class RevocationRecord:
    serial: str
    reason: str | None
    revoked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CRLStore:
    """Stores revoked certificates until a proper backing store is wired up."""

    def __init__(self) -> None:
        self._records: dict[str, RevocationRecord] = {}

    def revoke(self, *, serial: str, reason: str | None) -> RevocationRecord:
        record = RevocationRecord(serial=serial, reason=reason)
        self._records[serial] = record
        return record

    def all_serials(self) -> list[str]:
        return sorted(self._records)

    def all_records(self) -> list[RevocationRecord]:
        return [self._records[serial] for serial in self.all_serials()]

    def clear(self) -> None:
        self._records.clear()


consent_registry = ConsentRegistry()
crl_store = CRLStore()


class TrainingOptInRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingOptInResponse(BaseModel):
    status: str
    subject: str
    token: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class RevokeSerialRequest(BaseModel):
    serial: str = Field(..., min_length=1)
    reason: str | None = None


class CRLResponse(BaseModel):
    serials: list[str]
    revocations: list[RevocationRecord]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/live")
def live():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.post("/consent/training/optin", response_model=TrainingOptInResponse)
def training_optin(payload: TrainingOptInRequest):
    record = consent_registry.opt_in(
        subject=payload.subject,
        token=payload.token,
        metadata=payload.metadata,
    )
    return TrainingOptInResponse(
        status="opted_in",
        subject=record.subject,
        token=record.token,
        metadata=record.metadata,
        timestamp=record.timestamp,
    )


@app.get("/consent/training/optin/{subject}", response_model=TrainingOptInResponse)
def get_training_optin(subject: str):
    record = consent_registry.get(subject)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subject not registered")
    return TrainingOptInResponse(
        status="opted_in",
        subject=record.subject,
        token=record.token,
        metadata=record.metadata,
        timestamp=record.timestamp,
    )


@app.post("/crl", status_code=status.HTTP_201_CREATED, response_model=RevocationRecord)
def revoke_serial(payload: RevokeSerialRequest):
    return crl_store.revoke(serial=payload.serial, reason=payload.reason)


@app.get("/crl", response_model=CRLResponse)
def crl():
    return CRLResponse(serials=crl_store.all_serials(), revocations=crl_store.all_records())
