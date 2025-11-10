"""Translator that converts the topology DSL into Docker primitives."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from .schemas import ContainerSpec, LinkSpec, Topology, TrafficControl


class TrafficControlHook(BaseModel):
    container: str
    network: str
    commands: List[str]


class DockerNetworkPlan(BaseModel):
    name: str
    driver: str = "bridge"
    subnet: str | None = None


class DockerContainerPlan(BaseModel):
    name: str
    image: str
    command: List[str] | None = None
    environment: Dict[str, str]
    networks: List[str]
    tc_hooks: List[TrafficControlHook] = Field(default_factory=list)


class DockerPlan(BaseModel):
    name: str
    networks: List[DockerNetworkPlan]
    containers: List[DockerContainerPlan]


class TopologyTranslator:
    """Convert validated topologies into docker execution plans."""

    def translate(self, topology: Topology) -> DockerPlan:
        networks = [
            DockerNetworkPlan(name=network.name, subnet=network.subnet)
            for network in topology.networks
        ]

        container_lookup = {container.name: container for container in topology.containers}
        tc_hooks_by_container: Dict[str, List[TrafficControlHook]] = {
            container.name: [] for container in topology.containers
        }

        for link in topology.links:
            self._append_tc_hooks(link=link, lookup=container_lookup, hooks=tc_hooks_by_container)

        containers = [
            DockerContainerPlan(
                name=container.name,
                image=container.image,
                command=container.command,
                environment=container.environment,
                networks=[interface.network for interface in container.interfaces],
                tc_hooks=tc_hooks_by_container[container.name],
            )
            for container in topology.containers
        ]

        return DockerPlan(name=topology.name, networks=networks, containers=containers)

    def _append_tc_hooks(
        self,
        *,
        link: LinkSpec,
        lookup: Dict[str, ContainerSpec],
        hooks: Dict[str, List[TrafficControlHook]],
    ) -> None:
        if link.traffic is None:
            return

        for endpoint in (link.source, link.target):
            container = lookup.get(endpoint)
            if container is None:
                continue
            commands = self._tc_commands(link.traffic)
            hooks[container.name].append(
                TrafficControlHook(container=container.name, network=link.network, commands=commands)
            )

    def _tc_commands(self, traffic: TrafficControl) -> List[str]:
        commands: List[str] = []
        parameters: List[str] = []
        if traffic.latency_ms:
            parameters.append(f"delay {traffic.latency_ms}ms")
        if traffic.bandwidth_mbps:
            parameters.append(f"rate {traffic.bandwidth_mbps}mbit")
        if traffic.loss_percent:
            parameters.append(f"loss {traffic.loss_percent}%")
        if parameters:
            commands.append("tc qdisc replace dev $IFACE root netem " + " ".join(parameters))
        return commands


__all__ = [
    "TopologyTranslator",
    "DockerPlan",
    "DockerNetworkPlan",
    "DockerContainerPlan",
    "TrafficControlHook",
]
