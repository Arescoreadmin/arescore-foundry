from datetime import datetime, timezone

from services.forensics_hub.api import database, decisions, forensics


def _session(tmp_path):
    engine = database.create_db_engine(f"sqlite:///{tmp_path}/forensics.db")
    database.initialize_database(engine)
    return database.Session(engine)


def test_verification_flags_tampered_record(tmp_path):
    session = _session(tmp_path)
    ts_one = datetime(2024, 2, 1, 8, 0, 0, tzinfo=timezone.utc)
    ts_two = datetime(2024, 2, 1, 8, 15, 0, tzinfo=timezone.utc)

    decisions.persist_decision(
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
            decision="allow",
            policy_version="v1",
            inputs_fingerprint="fp-2",
        ),
        chain_ts=ts_two,
    )

    session.conn.execute(
        "UPDATE decisions SET decision = ? WHERE id = ?",
        ("tampered", second.id),
    )
    session.commit()

    result = forensics.verify_chain_for_tenant(session, "tenant-a")
    assert result["ok"] is False
    assert result["first_bad_id"] == second.id
