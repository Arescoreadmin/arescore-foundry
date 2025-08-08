import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from orchestrator.main import app as orchestrator_app
from sentinel_core.main import app as core_app
from sentinel_red.main import app as red_app
from log_indexer.main import app as log_app


def test_orchestrator_health():
    client = TestClient(orchestrator_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_sentinel_core_health():
    client = TestClient(core_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_sentinel_red_health():
    client = TestClient(red_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_log_indexer_health():
    client = TestClient(log_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
