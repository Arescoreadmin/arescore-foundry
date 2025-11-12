import itertools

from app.rag_cache.utils import chunk_iter


def test_chunk_iter_respects_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = list(chunk_iter(text, chunk_size=10, overlap=3))

    assert chunks[0] == text[:10]
    assert chunks[1] == text[7:17]
    assert chunks[2] == text[14:24]


def test_chunk_iter_progresses_when_overlap_ge_chunk():
    text = "abcdef"
    chunks = list(itertools.islice(chunk_iter(text, chunk_size=3, overlap=10), 4))

    assert chunks[:3] == ["abc", "bcd", "cde"]
    # ensure we eventually reach the tail of the string
    assert chunks[-1] == "def"
