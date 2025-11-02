from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health(): return {"ok": True}
@app.get("/ping")
def ping(): return {"pong": True}
