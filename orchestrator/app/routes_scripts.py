from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess

router = APIRouter()

app = FastAPI(title="Orchestrator")

# CORS so frontend at :3000 can call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    # Add real readiness checks later (deps, migrations, etc.)
    return {"ready": True, "svc": SERVICE}