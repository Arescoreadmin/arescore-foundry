from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ..crl import CRLParseError, crl_fingerprint, extract_revocations


def _build_crl(serial_numbers: list[int]) -> bytes:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)

    builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "arescore-ca")]))
        .last_update(now)
        .next_update(now + timedelta(days=7))
    )

    for serial in serial_numbers:
        revoked = (
            x509.RevokedCertificateBuilder()
            .serial_number(serial)
            .revocation_date(now)
            .build()
        )
        builder = builder.add_revoked_certificate(revoked)

    crl = builder.sign(private_key=private_key, algorithm=hashes.SHA256())
    return crl.public_bytes(encoding=serialization.Encoding.DER)


def test_extract_revocations_returns_expected_runtime_ids() -> None:
    payload = _build_crl([0x1234, 0xABCDEF])
    snapshot = extract_revocations(payload)

    assert snapshot.runtime_ids == ["1234", "abcdef"]
    assert snapshot.this_update.tzinfo == timezone.utc
    assert snapshot.next_update is not None


def test_crl_fingerprint_is_stable() -> None:
    payload = _build_crl([1])
    fingerprint = crl_fingerprint(payload)

    assert len(fingerprint) == 64
    assert fingerprint == crl_fingerprint(payload)


def test_invalid_crl_raises() -> None:
    try:
        extract_revocations(b"not-a-crl")
    except CRLParseError:
        return
    assert False, "Expected CRLParseError"
