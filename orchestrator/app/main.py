from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os

from common.logging import emit as emit_log

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


@app.on_event("startup")
async def startup_event() -> None:
    emit_log({"event": "startup", "service": SERVICE})


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    emit_log(
        {
            "event": "request",
            "service": SERVICE,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
        }
    )
    return response

@app.get("/health")
def health():
    return {"status": "ok", "svc": SERVICE}

@app.get("/ready")
def ready():
    # Add real readiness checks later (deps, migrations, etc.)
    return {"ready": True, "svc": SERVICE}
