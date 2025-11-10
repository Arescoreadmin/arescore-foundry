from __future__ import annotations

import pytest

from backend.orchestrator.app.schemas import Topology


VALID_YAML = """
name: demo
containers:
  - name: web
    image: nginx:alpine
    interfaces:
      - network: net0
  - name: db
    image: postgres:alpine
    interfaces:
      - network: net0
networks:
  - name: net0
    subnet: 10.0.0.0/24
links:
  - source: web
    target: db
    network: net0
    traffic:
      latency_ms: 10
      bandwidth_mbps: 100
"""


def test_topology_from_yaml_validates() -> None:
    topology = Topology.from_yaml(VALID_YAML)
    assert topology.name == "demo"
    assert len(topology.containers) == 2
    assert topology.links[0].traffic.latency_ms == 10


def test_invalid_link_reference_raises() -> None:
    bad_yaml = VALID_YAML.replace("db", "missing", 1)
    with pytest.raises(ValueError):
        Topology.from_yaml(bad_yaml)
