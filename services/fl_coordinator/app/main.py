from fastapi import FastAPI

app = FastAPI(title="{{SERVICE_NAME}}".replace("{{SERVICE_NAME}}", __name__.split(".")[0]))

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/live")
def live():
    return {"status": "alive"}

@app.get("/ready")
def ready():
    # future: check dependencies here (DB, message bus, etc.)
    return {"status": "ready"}
