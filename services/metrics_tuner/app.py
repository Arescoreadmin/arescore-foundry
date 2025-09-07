from fastapi import FastAPI
import threading, time, importlib
app = FastAPI()
@app.get("/health")
def health():
    return {"status": "ok"}
def _bg():
    try:
        cron = importlib.import_module("cron")
        fn = getattr(cron, "main", None) or getattr(cron, "run", None)
        if callable(fn): fn()
        else:
            while True: time.sleep(60)
    except Exception:
        while True: time.sleep(60)
t = threading.Thread(target=_bg, daemon=True)
t.start()