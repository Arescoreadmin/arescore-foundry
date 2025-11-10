from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from cryptography import x509
from cryptography.hazmat.primitives import hashes


class CRLParseError(RuntimeError):
    """Raised when the provided CRL payload cannot be parsed."""


@dataclass(frozen=True)
class RevocationSnapshot:
    runtime_ids: List[str]
    this_update: datetime
    next_update: datetime | None

    def as_dict(self) -> dict:
        return {
            "runtime_ids": self.runtime_ids,
            "this_update": self.this_update.isoformat(),
            "next_update": self.next_update.isoformat() if self.next_update else None,
        }


def _load_crl(document: bytes) -> x509.CertificateRevocationList:
    """Attempt to load a CRL as PEM and fall back to DER."""
    try:
        return x509.load_pem_x509_crl(document)
    except ValueError as pem_error:
        try:
            return x509.load_der_x509_crl(document)
        except ValueError as der_error:
            raise CRLParseError("Unable to decode CRL as PEM or DER") from der_error
        except Exception as exc:  # pragma: no cover - defensive
            raise CRLParseError("Unexpected error while decoding DER CRL") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise CRLParseError("Unexpected error while decoding PEM CRL") from exc


def extract_revocations(document: bytes) -> RevocationSnapshot:
    """Parse a CRL payload and normalise it for policy consumption."""
    crl = _load_crl(document)

    runtime_ids = [
        format(revoked.serial_number, "x")
        for revoked in crl
    ]

    if hasattr(crl, "last_update_utc"):
        this_update = crl.last_update_utc
    else:
        this_update = crl.last_update.replace(tzinfo=timezone.utc)

    if hasattr(crl, "next_update_utc"):
        next_update = crl.next_update_utc
    else:
        next_update = crl.next_update
        if next_update is not None and next_update.tzinfo is None:
            next_update = next_update.replace(tzinfo=timezone.utc)

    return RevocationSnapshot(runtime_ids=runtime_ids, this_update=this_update, next_update=next_update)


def crl_fingerprint(document: bytes) -> str:
    """Return a SHA256 fingerprint for caching/logging purposes."""
    digest = hashes.Hash(hashes.SHA256())
    digest.update(document)
    return digest.finalize().hex()
