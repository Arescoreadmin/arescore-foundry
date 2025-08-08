from fastapi import FastAPI

app = FastAPI(title="Sentinel Core")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/defend")
def defend(event: dict) -> dict:
    """Placeholder defense endpoint."""
    return {"action": "analyze", "event": event}
