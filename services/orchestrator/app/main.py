from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

# Optional root for sanity
@app.get("/")
def root():
    return {"service": "orchestrator", "status": "ready"}
