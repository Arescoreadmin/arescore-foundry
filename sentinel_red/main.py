from fastapi import FastAPI

app = FastAPI(title="Sentinel Red")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/attack")
def attack(target: dict) -> dict:
    """Placeholder attack endpoint."""
    return {"action": "probe", "target": target}
