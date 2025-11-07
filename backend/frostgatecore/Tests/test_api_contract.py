import os, time, httpx
BASE = os.getenv("BASE_URL","http://localhost:8000")
def wait_healthy(timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = httpx.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                j = r.json()
                if j.get("ok") is True or j.get("status") == "ok":
                    return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("service not healthy")
def test_health_and_cache_flow():
    wait_healthy()
