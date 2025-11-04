from fastapi import FastAPI

app = FastAPI(title="consent_registry")

@app.get("/health")
def health(): return {"ok": True}

@app.get("/live")
def live(): return {"status": "alive"}

@app.get("/ready")
def ready(): return {"status": "ready"}

# Expected by smokes:
@app.post("/consent/training/optin")
def training_optin():
    # TODO: persist subject/token, etc.
    return {"status": "opted_in", "subject": None}

@app.get("/crl")
def crl():
    # TODO: wire to real CRL backing store
    return {"serials": []}
