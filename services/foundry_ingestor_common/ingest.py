"""Ingestion routines for canonical models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .database import Session
from .models import NetworkSegment, Snapshot


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

    existing = session.get_snapshot(service, snapshot_id)
    if existing:
        return existing, False

    site_data = payload["site"]
    site = session.get_site_by_code(site_data["code"])
    if site is None:
        site = session.create_site(site_data)
    else:
        site.update_from_payload(site_data)
        session.update_site(site)

    segments_payload = {segment["code"]: segment for segment in payload.get("network_segments", [])}

    segment_by_code: dict[str, NetworkSegment] = {}
    for code, segment_payload in segments_payload.items():
        segment = session.get_segment(site.id, code)
        if segment is None:
            segment = session.create_segment(site.id, segment_payload)
        else:
            segment.update_from_payload(segment_payload)
            session.update_segment(segment)
        segment_by_code[code] = segment

    devices_payload = payload.get("devices", [])
    for device_payload in devices_payload:
        segment_code = device_payload.get("segment_code")
        segment_id = None
        if segment_code:
            segment = segment_by_code.get(segment_code)
            if segment is None:
                segment = session.get_segment(site.id, segment_code)
                if segment is None:
                    raise ValueError(
                        f"Segment code '{segment_code}' missing for device '{device_payload['code']}'"
                    )
                segment_by_code[segment_code] = segment
            segment_id = segment.id

        device = session.get_device(site.id, device_payload["code"])
        if device is None:
            session.create_device(site.id, device_payload, segment_id)
        else:
            device.segment_id = segment_id
            device.update_from_payload(device_payload)
            session.update_device(device)

    collected_at = _parse_datetime(payload.get("collected_at"))

    current_version = session.get_max_snapshot_version(service, site.id)
    next_version = (current_version or 0) + 1

    snapshot = session.create_snapshot(
        service=service,
        category=category,
        payload=payload,
        site_id=site.id,
        version=next_version,
        collected_at=collected_at,
    )

    return snapshot, True
