"""Abstractions around the task memory vector store (Qdrant with local fallback)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import httpx
import math

from .embedding import embed_text


@dataclass
class MemoryRecord:
    """Representation of a memory stored in the vector database."""

    task_id: str
    content: str
    vector: Iterable[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskMemory:
    """Simple interface expected by the :class:`ReasoningEngine`."""

    async def retrieve(self, task_id: str, query: str, top_k: int = 3) -> List[MemoryRecord]:  # pragma: no cover - interface
        raise NotImplementedError

    async def store(self, record: MemoryRecord) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class QdrantTaskMemory(TaskMemory):
    """Implementation backed by Qdrant with an in-memory fallback for offline testing."""

    def __init__(
        self,
        base_url: str = "http://qdrant:6333",
        collection: str = "task_memory",
        *,
        timeout: float = 5.0,
        local_fallback: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection = collection
        self.timeout = timeout
        self.local_fallback = local_fallback
        self._local_records: List[MemoryRecord] = []
        self._collection_ready = asyncio.Lock()
        self._collection_created = False

    async def _request(self, method: str, path: str, json: Optional[Dict[str, Any]] = None) -> Optional[httpx.Response]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.request(method, url, json=json)
                resp.raise_for_status()
                return resp
        except (httpx.RequestError, httpx.HTTPStatusError):
            if not self.local_fallback:
                raise
            return None

    async def _ensure_collection(self) -> None:
        if self._collection_created:
            return
        async with self._collection_ready:
            if self._collection_created:
                return
            payload = {
                "vectors": {
                    "size": 64,
                    "distance": "Cosine",
                }
            }
            await self._request("PUT", f"/collections/{self.collection}", json=payload)
            self._collection_created = True

    async def retrieve(self, task_id: str, query: str, top_k: int = 3) -> List[MemoryRecord]:
        await self._ensure_collection()
        query_vector = embed_text(query)
        payload = {
            "vector": query_vector,
            "limit": top_k,
            "filter": {
                "must": [
                    {
                        "key": "task_id",
                        "match": {"value": task_id},
                    }
                ]
            },
        }
        resp = await self._request("POST", f"/collections/{self.collection}/points/search", json=payload)
        if resp is None:
            return self._fallback_search(task_id, query_vector, top_k)
        data = resp.json()
        hits = data.get("result", [])
        results: List[MemoryRecord] = []
        for hit in hits:
            payload = hit.get("payload") or {}
            results.append(
                MemoryRecord(
                    task_id=payload.get("task_id", task_id),
                    content=payload.get("content", ""),
                    vector=hit.get("vector", query_vector),
                    metadata=payload,
                )
            )
        return results

    async def store(self, record: MemoryRecord) -> None:
        await self._ensure_collection()
        payload = {
            "points": [
                {
                    "id": record.metadata.get("id") if record.metadata else None,
                    "vector": list(record.vector),
                    "payload": {
                        "task_id": record.task_id,
                        "content": record.content,
                        **record.metadata,
                    },
                }
            ]
        }
        resp = await self._request("PUT", f"/collections/{self.collection}/points", json=payload)
        if resp is None and self.local_fallback:
            self._local_records.append(record)

    def _fallback_search(self, task_id: str, query_vector: Iterable[float], top_k: int) -> List[MemoryRecord]:
        if not self._local_records:
            return []

        def cosine(a: List[float], b: List[float]) -> float:
            if not a or not b:
                return 0.0
            length = min(len(a), len(b))
            dot = sum(a[i] * b[i] for i in range(length))
            norm_a = math.sqrt(sum(value * value for value in a[:length]))
            norm_b = math.sqrt(sum(value * value for value in b[:length]))
            if norm_a == 0.0 or norm_b == 0.0:
                return 0.0
            return dot / (norm_a * norm_b)

        query_vec = list(query_vector)
        scores: List[tuple[float, MemoryRecord]] = []
        for record in self._local_records:
            if record.task_id != task_id:
                continue
            rec_vec = list(record.vector)
            scores.append((cosine(rec_vec, query_vec), record))
        scores.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scores[:top_k]]
