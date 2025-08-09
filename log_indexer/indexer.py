from fastapi import FastAPI, Request, HTTPException
import uvicorn, os, hashlib, json, time

app = FastAPI()
SECRET = os.getenv("LOG_TOKEN","changeme-dev")
_prev = "0"*64

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"ready": True}

@app.post("/log")
async def log(req: Request):
    global _prev
    if req.headers.get("authorization","") != f"Bearer {SECRET}":
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await req.json()
    payload = json.dumps(body, sort_keys=True)
    chain = hashlib.sha256((_prev + payload).encode()).hexdigest()
    _prev = chain
    print(time.strftime("%H:%M:%S"), chain, payload, flush=True)
    return {"ok": True, "hash": chain}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
