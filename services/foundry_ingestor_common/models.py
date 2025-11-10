"""Canonical SQLAlchemy models shared by ingestor services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for canonical tables."""

    pass


class TimestampMixin:
    """Mixin that adds created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Site(Base, TimestampMixin):
    """Physical or logical site definition."""

    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    segments: Mapped[list["NetworkSegment"]] = relationship(
        "NetworkSegment",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    snapshots: Mapped[list["Snapshot"]] = relationship("Snapshot", back_populates="site")

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        self.name = payload.get("name", self.name)
        self.description = payload.get("description")
        self.metadata_ = payload.get("metadata", self.metadata_)


class NetworkSegment(Base, TimestampMixin):
    """Network segment information for a site."""

    __tablename__ = "network_segments"
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_segment_site_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    site_id: Mapped[str] = mapped_column(String(36), ForeignKey("sites.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cidr: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    site: Mapped[Site] = relationship("Site", back_populates="segments")
    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="segment",
        cascade="all, delete-orphan",
    )

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        self.name = payload.get("name", self.name)
        self.cidr = payload.get("cidr")
        self.metadata_ = payload.get("metadata", self.metadata_)


class Device(Base, TimestampMixin):
    """Device inventory entry."""

    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("segment_id", "code", name="uq_device_segment_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    site_id: Mapped[str] = mapped_column(String(36), ForeignKey("sites.id", ondelete="CASCADE"))
    segment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("network_segments.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    device_type: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    site: Mapped[Site] = relationship("Site")
    segment: Mapped[NetworkSegment | None] = relationship("NetworkSegment", back_populates="devices")

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        self.hostname = payload.get("hostname", self.hostname)
        self.ip_address = payload.get("ip_address")
        self.device_type = payload.get("device_type")
        self.metadata_ = payload.get("metadata", self.metadata_)


class Snapshot(Base):
    """Snapshot of ingested data from a source system."""

    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_snapshot_source_external_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    site_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sites.id"), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), nullable=False)

    site: Mapped[Site | None] = relationship("Site", back_populates="snapshots")

