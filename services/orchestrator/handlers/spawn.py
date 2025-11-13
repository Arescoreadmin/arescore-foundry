"""Spawn handler that maps scenario tracks to service calls."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from ..overlay_client import create_overlay, provision_voice


def get_default_actions() -> Dict[str, Any]:
    return {
        "network": {
            "type": "vxlan",
            "vni": 1001,
            "mtu": 1600,
            "ports": [4789],
        },
        "voice": {
            "secure": True,
            "dscp": 46,
            "codec": "opus",
        },
    }


async def handle_spawn(track: str) -> Dict[str, Any]:
    actions = get_default_actions()
    if track == "network":
        spec = actions["network"]
        return await create_overlay(spec)
    if track == "voice":
        spec = actions["voice"]
        return await provision_voice(spec)
    return {"result": "noop", "track": track}


if __name__ == "__main__":
    for track in ("network", "voice", "unknown"):
        print(asyncio.run(handle_spawn(track)))
