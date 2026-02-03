from services.forensics_hub.api import auth, database


def _session(tmp_path):
    engine = database.create_db_engine(f"sqlite:///{tmp_path}/forensics.db")
    database.initialize_database(engine)
    return database.Session(engine)


def test_new_keys_use_argon2id(tmp_path):
    session = _session(tmp_path)
    raw_key = auth.create_api_key(session, tenant_id="tenant-a", scopes=["decisions:read"])
    key_id = raw_key.split(".", 1)[0].replace(auth.API_KEY_PREFIX, "")

    row = session.conn.execute(
        "SELECT hash_alg, hash_params FROM api_keys WHERE id = ?",
        (key_id,),
    ).fetchone()
    assert row["hash_alg"] == auth.ARGON2ID
    assert row["hash_params"] != "{}"


def test_legacy_sha256_is_upgraded_on_verify(tmp_path):
    session = _session(tmp_path)
    key_id = "legacy1234"
    secret = "legacy-secret"
    auth.insert_legacy_sha256_key(
        session,
        key_id=key_id,
        secret=secret,
        tenant_id="tenant-a",
        scopes=["decisions:read"],
    )

    principal = auth.verify_api_key_detailed(
        session,
        f"{auth.API_KEY_PREFIX}{key_id}.{secret}",
        required_scopes=set(),
    )
    assert principal.key_id == key_id

    row = session.conn.execute(
        "SELECT hash_alg FROM api_keys WHERE id = ?",
        (key_id,),
    ).fetchone()
    assert row["hash_alg"] == auth.ARGON2ID
