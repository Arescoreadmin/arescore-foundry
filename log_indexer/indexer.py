from fastapi import FastAPI, Request, HTTPException
import uvicorn, os, hashlib, json, time

app = FastAPI()
SECRET = os.getenv("LOG_TOKEN","changeme-dev")
_prev = "0"*64

@app.get("/health")
def health():
    return {"status": "ok"}

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
# --- HEALTHCHECK PATCH START ---
# Minimal HTTP health/ready/live on :8080; becomes 500 if no progress for HEALTH_STALE_AFTER seconds (default 120s).
try:
    import time, json, os, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    _hc_start = time.time(); _hc_last_ok = _hc_start
    def mark_indexer_progress():
        global _hc_last_ok; _hc_last_ok = time.time()
    class _HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/health", "/ready", "/live"):
                age = time.time() - _hc_last_ok
                status = 200 if age < float(os.getenv("HEALTH_STALE_AFTER", "120")) else 500
                body = json.dumps({"status":"ok" if status==200 else "stale",
                                   "uptime_s":round(time.time()-_hc_start,3),
                                   "age_since_last_ok_s":round(age,3)})
                self.send_response(status); self.send_header("Content-Type","application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body.encode("utf-8"))
            else: self.send_response(404); self.end_headers()
        def log_message(self, *a, **k): return
    def _health_server():
        port = int(os.getenv("HEALTH_PORT", "8080"))
        srv = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
        srv.daemon_threads = True; srv.serve_forever()
    threading.Thread(target=_health_server, daemon=True).start()
except Exception: pass
# --- HEALTHCHECK PATCH END ---
