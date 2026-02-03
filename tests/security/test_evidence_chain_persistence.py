from datetime import datetime, timezone

from services.forensics_hub.api import database, decisions, forensics


def _session(tmp_path):
    engine = database.create_db_engine(f"sqlite:///{tmp_path}/forensics.db")
    database.initialize_database(engine)
    return database.Session(engine)


def test_chain_persists_and_is_tenant_scoped(tmp_path):
    session = _session(tmp_path)
    ts_one = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts_two = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)

    first = decisions.persist_decision(
        session,
        decisions.DecisionInput(
            tenant_id="tenant-a",
            request_id="req-1",
            decision="allow",
            policy_version="v1",
            inputs_fingerprint="fp-1",
        ),
        chain_ts=ts_one,
    )
    second = decisions.persist_decision(
        session,
        decisions.DecisionInput(
            tenant_id="tenant-a",
            request_id="req-2",
            decision="deny",
            policy_version="v1",
            inputs_fingerprint="fp-2",
        ),
        chain_ts=ts_two,
    )
    assert second.prev_hash == first.chain_hash

    payload = forensics.DecisionPayload(
        tenant_id="tenant-a",
        request_id="req-2",
        decision="deny",
        policy_version="v1",
        inputs_fingerprint="fp-2",
        chain_ts=ts_two,
    )
    expected = forensics.compute_chain_hash(first.chain_hash, payload)
    assert second.chain_hash == expected

    other = decisions.persist_decision(
        session,
        decisions.DecisionInput(
            tenant_id="tenant-b",
            request_id="req-3",
            decision="allow",
            policy_version="v2",
            inputs_fingerprint="fp-3",
        ),
        chain_ts=ts_one,
    )
    assert other.prev_hash == forensics.GENESIS_HASH
