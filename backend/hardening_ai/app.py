from fastapi import FastAPI
from pydantic import BaseModel
import os, subprocess, tempfile, json

REPO_URL = os.getenv("REPO_URL", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
NGINX_DIR = os.getenv("NGINX_DIR", "/work/nginx")
INFRA_DIR = os.getenv("INFRA_DIR", "/work/infra")

app = FastAPI(title="Hardening AI", version="0.1")

class Proposal(BaseModel):
    changes: list[str]  # names of scripts to run
    auto_apply: bool = False

@app.post("/propose")
async def propose():
    # Stub: inspect files and return a hardening plan
    plan = ["scripts/nginx_quick_headers.sh", "scripts/harden_infra.sh"]
    return {"plan": plan}

@app.post("/apply")
async def apply(p: Proposal):
    results = []
    for script in p.changes:
        try:
            out = subprocess.check_output(["bash", script], stderr=subprocess.STDOUT)
            results.append({"script": script, "ok": True, "out": out.decode()})
        except subprocess.CalledProcessError as e:
            results.append({"script": script, "ok": False, "out": e.output.decode()})
    return {"results": results}
@app.get("/health")
async def health():
    return {"ok": True}
