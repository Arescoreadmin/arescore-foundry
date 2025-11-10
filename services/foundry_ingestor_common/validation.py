"""Simplified JSON validation for ingestor payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class ValidationError(Exception):
    """Raised when a payload fails structural validation."""


class SnapshotValidator:
    """Validate payloads against the bundled snapshot schema.

    The implementation intentionally focuses on the subset of draft-07 features
    exercised by the unit tests: required fields, basic type checks and the ISO
    timestamp format used by ``collected_at``.
    """

    def __init__(self, schema: dict[str, Any]):
        self._schema = schema
        self._site_required = set(schema["properties"]["site"].get("required", []))
        self._segment_required = set(
            schema["properties"]["network_segments"]["items"].get("required", [])
        )
        self._device_required = set(schema["properties"]["devices"]["items"].get("required", []))
        self._top_level_required = set(schema.get("required", []))

    def validate(self, payload: dict[str, Any]) -> None:
        self._ensure_type(payload, dict, "payload")
        self._require_fields(payload, self._top_level_required, "payload")

        self._validate_site(payload.get("site"))
        self._validate_segments(payload.get("network_segments"))
        self._validate_devices(payload.get("devices"))
        self._validate_collected_at(payload.get("collected_at"))

    def _validate_site(self, site: Any) -> None:
        self._ensure_type(site, dict, "site")
        self._require_fields(site, self._site_required, "site")
        self._ensure_type(site.get("code"), str, "site.code")
        self._ensure_type(site.get("name"), str, "site.name")
        if "metadata" in site and not isinstance(site["metadata"], dict):
            raise ValidationError("site.metadata must be an object")

    def _validate_segments(self, segments: Any) -> None:
        self._ensure_type(segments, list, "network_segments")
        for index, segment in enumerate(segments):
            path = f"network_segments[{index}]"
            self._ensure_type(segment, dict, path)
            self._require_fields(segment, self._segment_required, path)
            self._ensure_type(segment.get("code"), str, f"{path}.code")
            self._ensure_type(segment.get("name"), str, f"{path}.name")
            if "metadata" in segment and not isinstance(segment["metadata"], dict):
                raise ValidationError(f"{path}.metadata must be an object")

    def _validate_devices(self, devices: Any) -> None:
        self._ensure_type(devices, list, "devices")
        for index, device in enumerate(devices):
            path = f"devices[{index}]"
            self._ensure_type(device, dict, path)
            self._require_fields(device, self._device_required, path)
            self._ensure_type(device.get("code"), str, f"{path}.code")
            self._ensure_type(device.get("hostname"), str, f"{path}.hostname")
            if "metadata" in device and not isinstance(device["metadata"], dict):
                raise ValidationError(f"{path}.metadata must be an object")
            if device.get("segment_code") is not None and not isinstance(
                device["segment_code"], str
            ):
                raise ValidationError(f"{path}.segment_code must be a string")

    def _validate_collected_at(self, value: Any) -> None:
        self._ensure_type(value, str, "collected_at")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValidationError("collected_at must be an ISO-8601 timestamp") from exc

    def _require_fields(self, container: dict[str, Any], required: set[str], path: str) -> None:
        missing = sorted(field for field in required if field not in container)
        if missing:
            raise ValidationError(f"{path} missing required field(s): {', '.join(missing)}")

    def _ensure_type(self, value: Any, expected: type, path: str) -> None:
        if not isinstance(value, expected):
            raise ValidationError(f"{path} must be of type {expected.__name__}")
