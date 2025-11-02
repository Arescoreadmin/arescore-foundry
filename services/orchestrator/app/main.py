from services._generated import federation_pb2, federation_pb2_grpc
sudo python3 - <<'PY'
from pathlib import Path
p = Path("/opt/arescore-foundry/services/orchestrator/app/main.py")
p.write_text('''\
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import http.client, json, os, logging

log = logging.getLogger("orchestrator")
app = FastAPI(title="orchestrator")

OPA_HOST = os.getenv("OPA_HOST", "opa")
OPA_PORT = int(os.getenv("OPA_PORT", "8181"))
OPA_PATH = "/v1/data/foundry/training/allow"

class Metadata(BaseModel):
    labels: list[str] = Field(default_factory=list)

class Limits(BaseModel):
    attacker_max_exploits: int

class Network(BaseModel):
    egress: str  # expect "deny"

class Scenario(BaseModel):
    metadata: Metadata
    limits: Limits
    network: Network

def opa_allow(scenario: dict) -> bool:
    body = json.dumps({"input": scenario})
    conn = http.client.HTTPConnection(OPA_HOST, OPA_PORT, timeout=3)
    try:
        conn.request("POST", OPA_PATH, body=body, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        text = res.read().decode() if res else ""
    except Exception as e:
        log.exception("OPA unreachable")
        raise HTTPException(status_code=502, detail=f"opa_unreachable: {e}")
    finally:
        try: conn.close()
        except Exception: pass

    if res is None or res.status >= 300:
        clipped = (text or "")[:300]
        log.error("OPA non-200: status=%s body=%s", getattr(res,'status',None), clipped)
        raise HTTPException(status_code=502, detail=f"opa_error status={getattr(res,'status',None)} body={clipped}")

    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError as e:
        log.error("OPA bad JSON: %r", text[:300])
        raise HTTPException(status_code=502, detail=f"opa_bad_json: {e}")

    return bool(data.get("result", False))

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/scenarios")
def create_scenario(s: Scenario):
    allowed = opa_allow(s.model_dump())
    return {"allowed": allowed}
''')
print("main.py bytes:", p.stat().st_size)
PY
