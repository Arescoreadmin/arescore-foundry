from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from .config import get_settings


class OPAClient:
    def __init__(self, base_url: str, policy_path: str) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.policy_path = policy_path

    async def authorize_spawn(self, payload: dict[str, Any]) -> None:
        if not self.base_url:
            return

        url = f"{self.base_url}{self.policy_path}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(url, json={"input": payload})
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"OPA request failed: {exc}",
                ) from exc

        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OPA responded with {response.status_code}: {response.text}",
            )

        result = response.json()
        allowed = result.get("result")
        if isinstance(allowed, dict):
            allowed = allowed.get("allow")

        if allowed is not True:
            message = "OPA rejected spawn request"
            if isinstance(result.get("result"), dict):
                message = result["result"].get("reason", message)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


_settings = get_settings()
opa_client = OPAClient(base_url=str(_settings.opa_url or ""), policy_path=_settings.opa_policy_path)
