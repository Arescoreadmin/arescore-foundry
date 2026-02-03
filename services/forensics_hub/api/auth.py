"""API key authentication and hashing helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, status

from .database import Session

API_KEY_PREFIX = "fgk_"
LEGACY_SHA256 = "sha256"
ARGON2ID = "argon2id"


@dataclass(frozen=True)
class Principal:
    key_id: str
    tenant_id: str | None
    scopes: set[str]


def _get_pepper() -> str:
    pepper = os.getenv("FG_KEY_PEPPER", "")
    if os.getenv("FG_ENV") == "production" and not pepper:
        raise RuntimeError("FG_KEY_PEPPER must be set in production")
    return pepper


def _argon2_hasher() -> PasswordHasher:
    return PasswordHasher(
        time_cost=int(os.getenv("FG_ARGON2_TIME_COST", "2")),
        memory_cost=int(os.getenv("FG_ARGON2_MEMORY_KIB", "65536")),
        parallelism=int(os.getenv("FG_ARGON2_PARALLELISM", "2")),
        hash_len=int(os.getenv("FG_ARGON2_HASH_LEN", "32")),
        salt_len=int(os.getenv("FG_ARGON2_SALT_LEN", "16")),
    )


def _hash_params() -> dict[str, int]:
    hasher = _argon2_hasher()
    return {
        "time_cost": hasher.time_cost,
        "memory_cost": hasher.memory_cost,
        "parallelism": hasher.parallelism,
        "hash_len": hasher.hash_len,
        "salt_len": hasher.salt_len,
    }


def _peppered(secret: str) -> str:
    pepper = _get_pepper()
    return f"{secret}{pepper}" if pepper else secret


def hash_key(secret: str) -> tuple[str, str, str]:
    hasher = _argon2_hasher()
    hashed = hasher.hash(_peppered(secret))
    return hashed, ARGON2ID, json.dumps(_hash_params(), sort_keys=True)


def _legacy_sha256(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_key(secret: str, *, hashed: str, alg: str) -> bool:
    if alg == ARGON2ID:
        hasher = _argon2_hasher()
        try:
            return hasher.verify(hashed, _peppered(secret))
        except VerifyMismatchError:
            return False
    if alg == LEGACY_SHA256:
        return hmac.compare_digest(_legacy_sha256(secret), hashed)
    return False


def _parse_api_key(raw_key: str) -> tuple[str, str]:
    if not raw_key.startswith(API_KEY_PREFIX):
        raise ValueError("API key format is invalid")
    try:
        key_id, secret = raw_key[len(API_KEY_PREFIX) :].split(".", 1)
    except ValueError as exc:
        raise ValueError("API key format is invalid") from exc
    if not key_id or not secret:
        raise ValueError("API key format is invalid")
    return key_id, secret


def create_api_key(
    session: Session,
    *,
    tenant_id: str | None,
    scopes: Iterable[str],
) -> str:
    key_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{key_id}.{secret}"
    hashed, alg, params = hash_key(secret)
    now = datetime.now(timezone.utc).isoformat()
    session.conn.execute(
        """
        INSERT INTO api_keys (id, tenant_id, scopes, hashed_key, hash_alg, hash_params, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            key_id,
            tenant_id,
            ",".join(sorted(set(scopes))),
            hashed,
            alg,
            params,
            now,
            now,
        ),
    )
    session.commit()
    return raw_key


def insert_legacy_sha256_key(
    session: Session,
    *,
    key_id: str,
    secret: str,
    tenant_id: str | None,
    scopes: Iterable[str],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session.conn.execute(
        """
        INSERT INTO api_keys (id, tenant_id, scopes, hashed_key, hash_alg, hash_params, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            key_id,
            tenant_id,
            ",".join(sorted(set(scopes))),
            _legacy_sha256(secret),
            LEGACY_SHA256,
            json.dumps({}, sort_keys=True),
            now,
            now,
        ),
    )
    session.commit()


def verify_api_key_detailed(
    session: Session,
    raw_key: str,
    *,
    required_scopes: set[str] | None = None,
) -> Principal:
    try:
        key_id, secret = _parse_api_key(raw_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    row = session.conn.execute(
        "SELECT id, tenant_id, scopes, hashed_key, hash_alg, hash_params FROM api_keys WHERE id = ?",
        (key_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key not found")

    alg = row["hash_alg"]
    hashed = row["hashed_key"]
    if not verify_key(secret, hashed=hashed, alg=alg):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key invalid")

    scopes = {scope for scope in row["scopes"].split(",") if scope}
    if required_scopes and not required_scopes.issubset(scopes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required scopes")

    if alg == LEGACY_SHA256:
        upgraded_hash, upgraded_alg, upgraded_params = hash_key(secret)
        session.conn.execute(
            """
            UPDATE api_keys
            SET hashed_key = ?, hash_alg = ?, hash_params = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                upgraded_hash,
                upgraded_alg,
                upgraded_params,
                datetime.now(timezone.utc).isoformat(),
                key_id,
            ),
        )
        session.commit()

    return Principal(key_id=key_id, tenant_id=row["tenant_id"], scopes=scopes)
