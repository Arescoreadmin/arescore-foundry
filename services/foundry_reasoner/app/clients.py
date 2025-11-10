"""HTTP clients used by the reasoner."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .schemas import ScenarioPlan


class OrchestratorClient:
    """Client for the orchestrator service."""

    def __init__(self, base_url: str = "http://orchestrator:8080") -> None:
        self.base_url = base_url.rstrip("/")

    async def create_scenario(self, plan: ScenarioPlan) -> str:
        url = f"{self.base_url}/api/scenarios"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=plan.dict())
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
        return str(data.get("id") or data.get("scenario_id") or "")


class PerformanceEvaluatorClient:
    """Client for the performance evaluator service."""

    def __init__(self, base_url: str = "http://performance_evaluator:8080") -> None:
        self.base_url = base_url.rstrip("/")

    async def evaluate(self, metrics: Dict[str, float]) -> float:
        if not metrics:
            return 50.0
        url = f"{self.base_url}/api/score"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json={"metrics": metrics})
            resp.raise_for_status()
            data = resp.json()
        return float(data.get("score", 50.0))


class DifficultyControllerClient:
    """Client for difficulty adjustment decisions."""

    def __init__(self, base_url: str = "http://difficulty_controller:8080") -> None:
        self.base_url = base_url.rstrip("/")

    async def adjust(self, current: str, score: float) -> Dict[str, Any]:
        url = f"{self.base_url}/api/difficulty"
        payload = {"current_difficulty": current, "score": score}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data


class LeaderboardClient:
    """Client for publishing outcomes to the leaderboard service."""

    def __init__(self, base_url: str = "http://leaderboard_service:8080") -> None:
        self.base_url = base_url.rstrip("/")

    async def publish(self, learner_id: Optional[str], score: float, difficulty: str, notes: str) -> None:
        if not learner_id:
            return
        url = f"{self.base_url}/api/leaderboard"
        payload = {
            "learner_id": learner_id,
            "score": score,
            "difficulty": difficulty,
            "notes": notes,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

    async def top(self, limit: int = 10) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/leaderboard"
        params = {"limit": limit}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        return list(data.get("entries", []))


class OPAClient:
    """OPA policy evaluation helper."""

    def __init__(self, url: str = "http://opa:8181/v1/data/foundry/reasoner/allow") -> None:
        self.url = url

    async def check(self, payload: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(self.url, json={"input": payload})
            resp.raise_for_status()
            data = resp.json()
        return bool(data.get("result", False))
