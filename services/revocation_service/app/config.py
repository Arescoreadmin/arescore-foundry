from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _as_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the revocation service."""

    crl_url: str = os.getenv("CRL_URL", "")
    crl_refresh_seconds: int = _as_int(os.getenv("CRL_REFRESH_SECONDS", "300"), 300)
    opa_base_url: str = os.getenv("OPA_BASE_URL", "http://opa:8181")
    opa_push_enabled: bool = _as_bool(os.getenv("OPA_PUSH_ENABLED", "true"), True)


settings = Settings()
