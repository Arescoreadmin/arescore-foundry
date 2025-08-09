from fastapi import FastAPI
import os

app = FastAPI()
SERVICE = os.getenv("SERVICE_NAME","orchestrator")

@app.get("/health")
def health(): return {"status":"ok","svc":SERVICE}

@app.get("/ready")
def ready(): return {"ready": True, "svc": SERVICE}
