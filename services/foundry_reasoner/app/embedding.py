"""Utility helpers for turning free-form text into deterministic embeddings."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable, List

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)


def _tokenize(text: str) -> Iterable[str]:
    for match in _TOKEN_RE.finditer(text.lower()):
        yield match.group(0)


def embed_text(text: str, dimensions: int = 64) -> List[float]:
    """Return a stable embedding vector for ``text`` using hashing.

    The approach deliberately avoids heavyweight ML dependencies while keeping
    deterministic behaviour that works well for similarity search in unit tests.
    """

    if not text:
        return [0.0] * dimensions

    vector = [0.0] * dimensions
    for token in _tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        weight = (int.from_bytes(digest[4:8], "big") % 1000) / 1000.0
        vector[idx] += 0.5 + weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
