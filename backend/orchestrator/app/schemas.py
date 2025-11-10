"""Pydantic models describing the topology DSL."""

from __future__ import annotations

from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class TrafficControl(BaseModel):
    latency_ms: Optional[float] = Field(default=None, ge=0)
    bandwidth_mbps: Optional[float] = Field(default=None, gt=0)
    loss_percent: Optional[float] = Field(default=None, ge=0, le=100)


class NetworkInterface(BaseModel):
    network: str
    ipv4_address: Optional[str] = Field(default=None, pattern=r"^\d+\.\d+\.\d+\.\d+/\d+$")


class ContainerSpec(BaseModel):
    name: str
    image: str
    command: Optional[List[str]] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    interfaces: List[NetworkInterface] = Field(default_factory=list)

    @field_validator("interfaces")
    @classmethod
    def ensure_unique_networks(cls, interfaces: List[NetworkInterface]) -> List[NetworkInterface]:
        networks = {iface.network for iface in interfaces}
        if len(networks) != len(interfaces):
            raise ValueError("Interfaces for a container must reference unique networks")
        return interfaces


class NetworkSpec(BaseModel):
    name: str
    subnet: Optional[str] = Field(default=None, pattern=r"^\d+\.\d+\.\d+\.\d+/\d+$")


class LinkSpec(BaseModel):
    source: str
    target: str
    network: str
    traffic: Optional[TrafficControl] = None


class Topology(BaseModel):
    name: str
    description: Optional[str] = None
    containers: List[ContainerSpec]
    networks: List[NetworkSpec] = Field(default_factory=list)
    links: List[LinkSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_topology(self) -> "Topology":
        container_names = {container.name for container in self.containers}
        for link in self.links:
            if link.source not in container_names:
                raise ValueError(f"Link references unknown source container '{link.source}'")
            if link.target not in container_names:
                raise ValueError(f"Link references unknown target container '{link.target}'")
        network_names = {network.name for network in self.networks}
        for container in self.containers:
            for interface in container.interfaces:
                if network_names and interface.network not in network_names:
                    raise ValueError(
                        f"Interface for container '{container.name}' references unknown network '{interface.network}'"
                    )
        return self

    @classmethod
    def from_yaml(cls, payload: str) -> "Topology":
        document = yaml.safe_load(payload)
        if not isinstance(document, dict):
            raise ValueError("Topology YAML must describe a mapping")
        return cls.model_validate(document)


__all__ = [
    "Topology",
    "ContainerSpec",
    "NetworkInterface",
    "NetworkSpec",
    "LinkSpec",
    "TrafficControl",
]
