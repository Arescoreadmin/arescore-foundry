param(
  [switch]$Commit
)

$ErrorActionPreference = 'Stop'
$appPath = "services/orchestrator/app/main.py"
if (!(Test-Path $appPath)) {
  throw "Not found: $appPath"
}

# Write dependency-aware FastAPI app
@"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, asyncio, httpx

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
RAW_DEPS = os.getenv("DEPENDENCY_URLS", "")
DEPENDENCY_URLS = [u.strip() for u in RAW_DEPS.split(",") if u.strip()]

@app.get("/health")
def health():
    return {"status": "ok", "svc": SERVICE}

async def _check_one(client: httpx.AsyncClient, url: str) -> dict:
    try:
        r = await client.get(url)
        return {"url": url, "status": r.status_code, "ok": r.status_code == 200}
    except Exception as e:
        return {"url": url, "error": str(e), "ok": False}

@app.get("/ready")
async def ready():
    if not DEPENDENCY_URLS:
        return {"ready": True, "svc": SERVICE, "checks": []}
    timeout = httpx.Timeout(2.0, connect=1.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(*[_check_one(client, u) for u in DEPENDENCY_URLS])
    overall = all(item.get("ok") for item in results)
    return {"ready": overall, "svc": SERVICE, "checks": results}
"@ | Set-Content $appPath -Encoding utf8

# Rebuild and restart orchestrator
Write-Host "[wire] Building orchestrator…" -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml --profile app build orchestrator | Out-Host
Write-Host "[wire] Restarting orchestrator…" -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml --profile app up -d orchestrator | Out-Host

# Figure mapped port
$line = docker port infra-orchestrator-1 8080 | Select-String '0\.0\.0\.0:' | Select-Object -First 1
$orchPort = if ($line) { ($line.ToString() -split ':')[-1].Trim() } else { 8080 }

# Wait for health/ready
function Wait-Ok($url, $secs=30) {
  $deadline = (Get-Date).AddSeconds($secs)
  do {
    try { $r = Invoke-RestMethod -UseBasicParsing -TimeoutSec 2 -Uri $url; return $true } catch { Start-Sleep 1 }
  } while ((Get-Date) -lt $deadline)
  return $false
}

if (!(Wait-Ok "http://localhost:$orchPort/health")) { throw "health failed" }
if (!(Wait-Ok "http://localhost:$orchPort/ready"))  { throw "ready failed"  }

# Optional commit
if ($Commit) {
  git add $appPath
  git commit -m "feat(orchestrator): /ready checks DEPENDENCY_URLS"
}

Write-Host "[wire] Done. /ready now validates dependencies listed in DEPENDENCY_URLS." -ForegroundColor Green
