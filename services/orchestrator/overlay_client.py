"""Async clients for overlay and voice services."""
from __future__ import annotations

import os
from typing import Any, Dict

import httpx

OVERLAY_URL = os.getenv("OVERLAY_URL", "http://network_overlay:8087")
VOICE_URL = os.getenv("VOICE_URL", "http://voice_gateway:8088")


async def create_overlay(spec: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{OVERLAY_URL}/create", json=spec)
        resp.raise_for_status()
        return resp.json()


async def provision_voice(spec: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{VOICE_URL}/provision", json=spec)
        resp.raise_for_status()
        return resp.json()
