from fastapi import FastAPI
from typing import Dict, Any, Optional
import os
import httpx

app = FastAPI(title="Observer Hub")

PROM_URL = os.getenv("PROM_URL", "http://prometheus:9090")
ALERT_URL = os.getenv("ALERT_URL", "http://alertmanager:9093")
LOG_INDEXER_URL = os.getenv("LOG_INDEXER_URL", "http://log_indexer:8081")


@app.get("/health")
async def health() -> Dict[str, Any]:
    """
    Health check endpoint.
    """
    return {"ok": True, "service": "observer_hub"}


async def safe_get_json(
    url: str,
    params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch JSON data from a URL, returning None on error.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Retrieve basic status from Prometheus and Alertmanager.
    """
    prom_status = await safe_get_json(f"{PROM_URL}/api/v1/status/runtimeinfo")
    alert_status = await safe_get_json(f"{ALERT_URL}/api/v2/status")
    return {"prometheus": prom_status, "alertmanager": alert_status}


@app.get("/risks")
async def get_risks() -> Dict[str, Any]:
    """
    Retrieve recent risks/alerts.
    """
    alerts = await safe_get_json(f"{ALERT_URL}/api/v2/alerts")
    return {"alerts": alerts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)
