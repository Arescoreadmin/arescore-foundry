from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Orchestrator")

# CORS so frontend at :3000 can call us (comma-separated env also supported)
allow_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allow_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICE = os.getenv("SERVICE_NAME", "orchestrator")

@app.get("/health")
def health():
    return {"status": "ok", "svc": SERVICE}

@app.get("/ready")
def ready():
    # plug your real readiness checks here
    return {"ready": True, "svc": SERVICE}