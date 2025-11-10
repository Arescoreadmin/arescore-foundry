"""Smoke tests for the simulation harness."""

import asyncio

from ..simulation import SimulationHarness


def test_simulation_harness_executes_reasoning_cycle():
    harness = SimulationHarness.build()
    result = asyncio.run(harness.run_once())

    assert result.allowed is True
    assert result.scenario_id.startswith("sim-")
    assert 0.0 <= result.score <= 100.0
    assert result.difficulty in {"easy", "medium", "hard"}
    assert result.recommendations
    assert result.decision_summary
