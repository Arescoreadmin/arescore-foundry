"""Base classes for overlay drivers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class OverlayDriver:
    name: str

    def create(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {"driver": self.name, "action": "create", "spec": spec}

    def delete(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        return {"driver": self.name, "action": "delete", "spec": spec}
