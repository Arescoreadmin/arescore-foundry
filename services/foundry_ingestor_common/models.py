"""Canonical data models used by ingestor services.

The original implementation depended on SQLAlchemy ORM models. To keep the
runtime footprint small for the kata environment we instead provide lightweight
``dataclass`` representations with helper constructors.  They expose the same
attributes that the tests rely on while remaining serialisable to and from the
SQLite backing store used by :mod:`services.foundry_ingestor_common.database`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TimestampMixin:
    """Mixin that adds created/updated timestamps."""

    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


@dataclass
class Site(TimestampMixin):
    """Physical or logical site definition."""

    table_name: ClassVar[str] = "sites"

    id: str = field(default_factory=lambda: str(uuid4()))
    code: str = ""
    name: str = ""
    description: str | None = None
    metadata_: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Site":
        return cls(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            description=row.get("description"),
            metadata_=row.get("metadata", {}),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        self.name = payload.get("name", self.name)
        self.description = payload.get("description")
        self.metadata_ = payload.get("metadata", self.metadata_)
        self.touch()


@dataclass
class NetworkSegment(TimestampMixin):
    """Network segment information for a site."""

    table_name: ClassVar[str] = "network_segments"

    id: str = field(default_factory=lambda: str(uuid4()))
    site_id: str = ""
    code: str = ""
    name: str = ""
    cidr: str | None = None
    metadata_: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "NetworkSegment":
        return cls(
            id=row["id"],
            site_id=row["site_id"],
            code=row["code"],
            name=row["name"],
            cidr=row.get("cidr"),
            metadata_=row.get("metadata", {}),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        self.name = payload.get("name", self.name)
        self.cidr = payload.get("cidr")
        self.metadata_ = payload.get("metadata", self.metadata_)
        self.touch()


@dataclass
class Device(TimestampMixin):
    """Device inventory entry."""

    table_name: ClassVar[str] = "devices"

    id: str = field(default_factory=lambda: str(uuid4()))
    site_id: str = ""
    segment_id: str | None = None
    code: str = ""
    hostname: str = ""
    ip_address: str | None = None
    device_type: str | None = None
    metadata_: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Device":
        return cls(
            id=row["id"],
            site_id=row["site_id"],
            segment_id=row.get("segment_id"),
            code=row["code"],
            hostname=row["hostname"],
            ip_address=row.get("ip_address"),
            device_type=row.get("device_type"),
            metadata_=row.get("metadata", {}),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        self.hostname = payload.get("hostname", self.hostname)
        self.ip_address = payload.get("ip_address")
        self.device_type = payload.get("device_type")
        self.metadata_ = payload.get("metadata", self.metadata_)
        self.touch()


@dataclass
class Snapshot:
    """Snapshot of ingested data from a source system."""

    table_name: ClassVar[str] = "snapshots"

    id: str = field(default_factory=lambda: str(uuid4()))
    external_id: str = ""
    source: str = ""
    category: str = ""
    version: int = 1
    site_id: str | None = None
    collected_at: datetime | None = None
    ingested_at: datetime = field(default_factory=_utcnow)
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Snapshot":
        collected_at = row.get("collected_at")
        return cls(
            id=row["id"],
            external_id=row["external_id"],
            source=row["source"],
            category=row["category"],
            version=row["version"],
            site_id=row.get("site_id"),
            collected_at=datetime.fromisoformat(collected_at) if collected_at else None,
            ingested_at=datetime.fromisoformat(row["ingested_at"]),
            payload=row.get("payload", {}),
        )


__all__ = ["Device", "NetworkSegment", "Site", "Snapshot"]
