from __future__ import annotations

from backend.orchestrator.app.schemas import Topology
from backend.orchestrator.app.translator import TopologyTranslator


def test_translator_generates_tc_commands() -> None:
    topology = Topology.from_yaml(
        """
        name: demo
        containers:
          - name: a
            image: alpine
            interfaces:
              - network: net0
          - name: b
            image: alpine
            interfaces:
              - network: net0
        networks:
          - name: net0
        links:
          - source: a
            target: b
            network: net0
            traffic:
              latency_ms: 25
              bandwidth_mbps: 5
              loss_percent: 0.1
        """
    )

    plan = TopologyTranslator().translate(topology)

    assert plan.containers[0].tc_hooks
    command = plan.containers[0].tc_hooks[0].commands[0]
    assert "delay 25" in command
    assert "rate 5" in command
    assert "loss 0.1" in command
