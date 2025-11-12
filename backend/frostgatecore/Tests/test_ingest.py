import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import ingest as ingest_mod

# -----------------------
# Fake MinIO client
# -----------------------
class _FakePutResult:
    etag = "fake-etag"

class FakeMinio:
    def __init__(self):
        self.buckets = set()
        self.objects = {}
    def bucket_exists(self, name): return name in self.buckets
    def make_bucket(self, name): self.buckets.add(name)
    def set_bucket_versioning(self, *a, **k): pass
    def put_object(self, bucket_name, object_name, data, length, content_type=None):
        assert bucket_name in self.buckets
        payload = data.read()
        assert len(payload) == length
        self.objects[(bucket_name, object_name)] = payload
        return _FakePutResult()
    def get_presigned_url(self, method, bucket, object_name, expires):
        return f"http://example.local/{bucket}/{object_name}?exp={int(expires.total_seconds())}"

@pytest.fixture
def fake_minio():
    return FakeMinio()

@pytest.fixture
def client(fake_minio, monkeypatch):
    # Pin router config
    monkeypatch.setattr(ingest_mod, "MAX_UPLOAD_BYTES", 50 * 1024 * 1024, raising=True)
    monkeypatch.setattr(ingest_mod, "ALLOW_CONTENT_TYPES",
                        {"application/pdf","text/plain","image/png","image/jpeg"}, raising=True)
    monkeypatch.setattr(ingest_mod, "DEFAULT_BUCKET", "ingest", raising=True)
    monkeypatch.setattr(ingest_mod, "ENABLE_PRESIGNED", False, raising=True)
    monkeypatch.setattr(ingest_mod, "PRESIGNED_EXPIRY_SEC", 900, raising=True)

    # 1) Test hook: force get_minio() to return fake BEFORE dependency resolution
    ingest_mod._set_test_fake_client(fake_minio)

    # 2) FastAPI dependency override (belt)
    app.dependency_overrides[ingest_mod.get_minio] = lambda: fake_minio

    # 3) If code tries to construct Minio directly, return fake (suspenders)
    try:
        import minio  # installed in venv
        monkeypatch.setattr(minio, "Minio", lambda *a, **k: fake_minio, raising=False)
    except Exception:
        pass
    # Also patch symbol on module in case it exists
    monkeypatch.setattr(ingest_mod, "Minio", lambda *a, **k: fake_minio, raising=False)

    # Assert the hook actually works right now
    assert ingest_mod.get_minio() is fake_minio

    c = TestClient(app)
    try:
        yield c
    finally:
        app.dependency_overrides.pop(ingest_mod.get_minio, None)
        ingest_mod._set_test_fake_client(None)

# -----------------------
# Tests
# -----------------------
def test_ingest_happy_path(client, fake_minio):
    buf = io.BytesIO(b"hello world")
    files = {"file": ("hello.txt", buf, "text/plain")}
    r = client.post("/api/ingest", files=files, headers={"tenant": "t1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bucket"] == "t1"
    assert body["object"] == "hello.txt"
    assert body["size"] == 11
    assert len(body["sha256"]) == 64
    assert ("t1", "hello.txt") in fake_minio.objects

def test_ingest_rejects_oversize_stream(client, monkeypatch):
    monkeypatch.setattr(ingest_mod, "MAX_UPLOAD_BYTES", 5, raising=True)
    data = io.BytesIO(b"123456")
    files = {"file": ("big.txt", data, "text/plain")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 413

def test_ingest_rejects_unsupported_content_type(client, monkeypatch):
    monkeypatch.setattr(ingest_mod, "ALLOW_CONTENT_TYPES", {"text/plain"}, raising=True)
    data = io.BytesIO(b"{}")
    files = {"file": ("data.json", data, "application/json")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 415

def test_ingest_with_presigned_enabled(client, fake_minio, monkeypatch):
    monkeypatch.setattr(ingest_mod, "ENABLE_PRESIGNED", True, raising=True)
    monkeypatch.setattr(ingest_mod, "PRESIGNED_EXPIRY_SEC", 123, raising=True)
    data = io.BytesIO(b"hello")
    files = {"file": ("p.txt", data, "text/plain")}
    r = client.post("/api/ingest", files=files, headers={"tenant": "presign"})
    assert r.status_code == 200
    body = r.json()
    assert "presigned_get" in body
    assert body["presigned_get_expires_sec"] == 123
    assert body["presigned_get"].startswith("http://example.local/presign/p.txt?")
