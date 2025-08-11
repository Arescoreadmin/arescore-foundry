from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"ready": True}
@app.get("/_healthz", include_in_schema=False)
async def _healthz():
    return {"status": "ok"}

# Alias for k8s-style health endpoint
app.add_api_route("/_healthz", health, include_in_schema=False)

app.add_api_route("/_healthz", health, include_in_schema=False)
