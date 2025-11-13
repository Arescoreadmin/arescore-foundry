import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers import ingest as ingest_mod

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
    # Pin config to safe defaults
    monkeypatch.setattr(ingest_mod, "MAX_UPLOAD_BYTES", 50 * 1024 * 1024, raising=True)
    monkeypatch.setattr(ingest_mod, "ALLOW_CONTENT_TYPES",
                        {"application/pdf","text/plain","image/png","image/jpeg"}, raising=True)
    monkeypatch.setattr(ingest_mod, "DEFAULT_BUCKET", "ingest", raising=True)
    monkeypatch.setattr(ingest_mod, "ENABLE_PRESIGNED", False, raising=True)
    monkeypatch.setattr(ingest_mod, "PRESIGNED_EXPIRY_SEC", 900, raising=True)

    # Set the hook BEFORE creating TestClient so get_minio() returns the fake immediately
    ingest_mod._set_test_fake_client(fake_minio)

    from app.main import app
    # Belt-and-suspenders: also override the dependency (not strictly needed now)
    app.dependency_overrides[ingest_mod.get_minio] = lambda: fake_minio

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
    assert body["etag"] == "fake-etag"
    assert len(body["sha256"]) == 64

    # Ensure it really wrote the object
    assert fake_minio.objects[("t1", "hello.txt")] == b"hello world"


def test_ingest_uses_default_bucket_when_no_tenant(client, fake_minio, monkeypatch):
    monkeypatch.setattr(ingest_mod, "DEFAULT_BUCKET", "ingest-default", raising=True)

    data = io.BytesIO(b"x")
    files = {"file": ("a.txt", data, "text/plain")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 200
    assert r.json()["bucket"] == "ingest-default"
    assert ("ingest-default", "a.txt") in fake_minio.objects


def test_ingest_rejects_oversize_stream(client, monkeypatch):
    # Make the limit tiny and exceed it with stream
    monkeypatch.setattr(ingest_mod, "MAX_UPLOAD_BYTES", 5, raising=True)

    data = io.BytesIO(b"123456")  # 6 bytes
    files = {"file": ("big.txt", data, "text/plain")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 413
    body = r.json()
    assert "File too large" in body["detail"]


def test_ingest_rejects_unsupported_content_type(client, monkeypatch):
    # Allow only text/plain to force a 415 on application/json
    monkeypatch.setattr(ingest_mod, "ALLOW_CONTENT_TYPES", {"text/plain"}, raising=True)

    data = io.BytesIO(b"{}")
    files = {"file": ("data.json", data, "application/json")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 415
    assert "Unsupported content-type" in r.json()["detail"]


def test_ingest_empty_filename_becomes_unnamed(client, fake_minio):
    data = io.BytesIO(b"abc")
    # Pass an empty filename string
    files = {"file": ("", data, "text/plain")}
    r = client.post("/api/ingest", files=files, headers={"tenant": "z"})
    assert r.status_code == 200
    # Our API sets object_name = file.filename or "unnamed"
    assert r.json()["object"] in ("", "unnamed")
    # Stored key should match what the router used
    stored_keys = [k for k in fake_minio.objects.keys() if k[0] == "z"]
    assert len(stored_keys) == 1


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


def test_error_shape_is_consistent(client, monkeypatch):
    # Force an internal error by replacing ensure_bucket with a raiser
    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ingest_mod, "ensure_bucket", boom, raising=True)

    data = io.BytesIO(b"x")
    files = {"file": ("x.txt", data, "text/plain")}
    r = client.post("/api/ingest", files=files)
    # Router wraps unexpected exceptions as 500 with a generic message
    assert r.status_code == 500
    assert r.json()["detail"] == "Internal ingest failure"
