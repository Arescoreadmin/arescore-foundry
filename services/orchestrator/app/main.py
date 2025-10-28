from fastapi import FastAPI, Request, HTTPException
import http.client
import os
import json
import uuid, json, logging

# OPA Policy Configuration
OPA_HOST = os.getenv("OPA_HOST", "opa")
OPA_PORT = int(os.getenv("OPA_PORT", "8181"))
OPA_PATH = "/v1/data/foundry/training/allow"

def opa_allow(scenario: dict) -> bool:
    """Check if scenario is allowed by OPA policy."""
    try:
        body = json.dumps({"input": scenario}).encode("utf-8")
        conn = http.client.HTTPConnection(OPA_HOST, OPA_PORT, timeout=3)
        conn.request("POST", OPA_PATH, body=body, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        
        if res.status >= 300:
            return False
        
        data = json.loads(res.read().decode() or "{}")
        return bool(data.get("result", False))
    except Exception as e:
        print(f"OPA_ERROR: {e}")
        return False
    finally:
        if conn:
            conn.close()


app = FastAPI(title="orchestrator-mock")
log = logging.getLogger("uvicorn.access")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/scenarios")

        async def create_scenario(req: Request):
    payload = await req.json()
    # OPA Policy Check
    if not opa_allow(payload):
        raise HTTPException(status_code=403, detail="scenario denied by policy")
    
    # tiny validation so we don't accept nonsense
    if "metadata" not in payload or "name" not in payload.get("metadata", {}):
        raise HTTPException(status_code=400, detail="missing metadata.name")
    sid = str(uuid.uuid4())[:8]
    # log it so you can inspect in docker logs
    log.info("SCENARIO_SUBMIT %s %s", sid, json.dumps(payload))
    # fake acceptance response (the spawn service just expects something parsable)
    return {"status": "accepted", "scenario_id": sid}
