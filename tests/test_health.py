import requests

def test_health_endpoints():
    ports = [8000, 8001, 8002, 8003, 8004]
    for port in ports:
        r = requests.get(f"http://localhost:{port}/health")
        assert r.status_code == 200
