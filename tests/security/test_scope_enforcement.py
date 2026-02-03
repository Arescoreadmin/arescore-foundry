from fastapi.testclient import TestClient

from services.forensics_hub.api import auth, database, server


def _session(database_url: str) -> database.Session:
    engine = database.create_db_engine(database_url)
    database.initialize_database(engine)
    return database.Session(engine)


def test_scope_enforcement_blocks_missing_scope(tmp_path):
    database_url = f"sqlite:///{tmp_path}/forensics.db"
    app = server.create_app(database_url)
    client = TestClient(app)

    session = _session(database_url)
    key_missing_scope = auth.create_api_key(
        session,
        tenant_id="tenant-a",
        scopes=["decisions:read"],
    )

    response = client.post(
        "/api/decisions",
        headers={"Authorization": f"Bearer {key_missing_scope}"},
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "decision": "allow",
            "policy_version": "v1",
            "inputs_fingerprint": "fp-1",
        },
    )
    assert response.status_code == 403


def test_scope_enforcement_allows_required_scope(tmp_path):
    database_url = f"sqlite:///{tmp_path}/forensics.db"
    app = server.create_app(database_url)
    client = TestClient(app)

    session = _session(database_url)
    key_with_scope = auth.create_api_key(
        session,
        tenant_id="tenant-a",
        scopes=["decisions:write", "decisions:read"],
    )

    response = client.post(
        "/api/decisions",
        headers={"Authorization": f"Bearer {key_with_scope}"},
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "decision": "allow",
            "policy_version": "v1",
            "inputs_fingerprint": "fp-1",
        },
    )
    assert response.status_code == 200
