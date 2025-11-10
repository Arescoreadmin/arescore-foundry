"""Ingestion routines for canonical models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Device, NetworkSegment, Site, Snapshot


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid datetime format: {value}") from exc


def ingest_snapshot(
    session: Session,
    *,
    service: str,
    category: str,
    payload: dict[str, Any],
) -> tuple[Snapshot, bool]:
    """Persist snapshot payload into canonical tables.

    Returns a tuple of ``(snapshot, created)`` where ``created`` indicates whether a
    new snapshot row was inserted.
    """

    snapshot_id = payload["snapshot_id"]

    existing = session.execute(
        select(Snapshot).where(Snapshot.source == service, Snapshot.external_id == snapshot_id)
    ).scalar_one_or_none()
    if existing:
        return existing, False

    site_data = payload["site"]
    site = session.execute(select(Site).where(Site.code == site_data["code"])).scalar_one_or_none()
    if site is None:
        site = Site(
            code=site_data["code"],
            name=site_data["name"],
            description=site_data.get("description"),
            metadata_=site_data.get("metadata", {}),
        )
        session.add(site)
    else:
        site.update_from_payload(site_data)

    session.flush()

    segments_payload = {segment["code"]: segment for segment in payload.get("network_segments", [])}

    segment_by_code: dict[str, NetworkSegment] = {}
    for code, segment_payload in segments_payload.items():
        segment = session.execute(
            select(NetworkSegment).where(
                NetworkSegment.site_id == site.id,
                NetworkSegment.code == code,
            )
        ).scalar_one_or_none()
        if segment is None:
            segment = NetworkSegment(
                site_id=site.id,
                code=code,
                name=segment_payload["name"],
                cidr=segment_payload.get("cidr"),
                metadata_=segment_payload.get("metadata", {}),
            )
            session.add(segment)
        else:
            segment.update_from_payload(segment_payload)
        session.flush()
        segment_by_code[code] = segment

    devices_payload = payload.get("devices", [])
    for device_payload in devices_payload:
        segment_code = device_payload.get("segment_code")
        segment_id = None
        if segment_code:
            segment = segment_by_code.get(segment_code)
            if segment is None:
                segment = session.execute(
                    select(NetworkSegment).where(
                        NetworkSegment.site_id == site.id,
                        NetworkSegment.code == segment_code,
                    )
                ).scalar_one_or_none()
                if segment is None:
                    raise ValueError(f"Segment code '{segment_code}' missing for device '{device_payload['code']}'")
                segment_by_code[segment_code] = segment
            segment_id = segment.id

        device = session.execute(
            select(Device).where(
                Device.site_id == site.id,
                Device.code == device_payload["code"],
            )
        ).scalar_one_or_none()
        if device is None:
            device = Device(
                site_id=site.id,
                segment_id=segment_id,
                code=device_payload["code"],
                hostname=device_payload["hostname"],
                ip_address=device_payload.get("ip_address"),
                device_type=device_payload.get("device_type"),
                metadata_=device_payload.get("metadata", {}),
            )
            session.add(device)
        else:
            device.segment_id = segment_id
            device.update_from_payload(device_payload)

    collected_at = _parse_datetime(payload.get("collected_at"))

    current_version = session.execute(
        select(func.max(Snapshot.version)).where(Snapshot.source == service, Snapshot.site_id == site.id)
    ).scalar_one()
    next_version = (current_version or 0) + 1

    snapshot = Snapshot(
        external_id=snapshot_id,
        source=service,
        category=category,
        version=next_version,
        site=site,
        collected_at=collected_at,
        payload=payload,
    )
    session.add(snapshot)

    try:
        session.flush()
    except IntegrityError as exc:  # pragma: no cover - safety
        raise ValueError(f"Unable to persist snapshot {snapshot_id}") from exc

    return snapshot, True
