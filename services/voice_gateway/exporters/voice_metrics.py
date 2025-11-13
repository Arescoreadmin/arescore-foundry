"""Placeholder exporter for voice telemetry."""


def collect() -> dict:
    return {"latency_ms": 10, "jitter_ms": 5, "loss_pct": 0.1}
