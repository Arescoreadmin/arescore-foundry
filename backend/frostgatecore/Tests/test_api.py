from fastapi.testclient import TestClient
from app.main import app

def _scrub(d):
    return {
        k: v
        for k, v in d.items()
        if k not in {"corr_id", "request_id", "ts", "model"}
    }

def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert (j.get("ok") is True) or (j.get("status") == "ok")

def test_embed_and_query_cache_behave():
    c = TestClient(app)
    e1 = c.post("/dev/embed", json={"text": "hello"})
    assert e1.status_code == 200
    e2 = c.post("/dev/embed", json={"text": "hello"})
    assert e2.status_code == 200
    assert _scrub(e1.json()) == _scrub(e2.json())

    q1 = c.get("/dev/q", params={"q": "ping", "k": 2})
    assert q1.status_code == 200
    q2 = c.get("/dev/q", params={"q": "ping", "k": 2})
    assert q2.status_code == 200
    assert _scrub(q1.json()) == _scrub(q2.json())
