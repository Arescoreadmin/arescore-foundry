import hashlib
from typing import Iterable

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def normalize_text(t: str) -> str:
    # cheap normalization: strip, collapse whitespace
    return " ".join(t.split())

def chunk_iter(text: str, chunk_size: int = 1000, overlap: int = 100) -> Iterable[str]:
    text = normalize_text(text)
    if chunk_size <= 0:
        yield text
        return
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + chunk_size)
        yield text[i:j]
        i = max(j - overlap, j)
