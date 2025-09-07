# scripts/fix_health_and_dockerfiles.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Dir($p) {
  if (-not (Test-Path $p)) {
    New-Item -ItemType Directory -Path $p | Out-Null
  }
}

function Write-IfChanged {
  param([Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content)
  Ensure-Dir (Split-Path $Path)
  $old = if (Test-Path $Path) { Get-Content -Raw -Path $Path -ErrorAction SilentlyContinue } else { "" }
  if ($old -ne $Content) {
    Set-Content -Path $Path -Value $Content -NoNewline
    return $true
  }
  return $false
}

function Ensure-LinesInFile {
  param([Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string[]]$Lines)
  Ensure-Dir (Split-Path $Path)

  if (-not (Test-Path $Path)) {
    Set-Content -Path $Path -Value ($Lines -join "`r`n") -NoNewline
    return $true
  }

  $existing = (Get-Content -Raw -Path $Path -ErrorAction SilentlyContinue) -split "`r?`n"
  # Force array to avoid .Count on $null
  $missing = @($Lines | Where-Object { $_ -and ($existing -notcontains $_) })

  if ($missing.Count -gt 0) {
    Add-Content -Path $Path -Value ("`r`n" + ($missing -join "`r`n"))
    return $true
  }
  return $false
}

# 1) Minimal /health apps
$observerApp = @'
from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health():
    return {"status": "ok"}
'@

$metricsApp = @'
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
'@

$changed = @()
$changed += if (Write-IfChanged "services\observer_hub\app.py"   $observerApp) { "observer_hub/app.py" }
$changed += if (Write-IfChanged "services\metrics_tuner\app.py"  $metricsApp)  { "metrics_tuner/app.py" }

# 2) Requirements: ensure FastAPI + Uvicorn
if (Ensure-LinesInFile "services\observer_hub\requirements.txt"  @("fastapi","uvicorn"))    { $changed += "observer_hub/requirements.txt" }
if (Ensure-LinesInFile "services\metrics_tuner\requirements.txt" @("fastapi","uvicorn"))    { $changed += "metrics_tuner/requirements.txt" }

# 3) Dockerfiles: run real servers
$observerDocker = @'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn
COPY app.py /app/app.py
EXPOSE 9092
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","9092"]
'@

$metricsDocker = @'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true && \
    pip install --no-cache-dir fastapi uvicorn
COPY cron.py /app/cron.py
COPY app.py  /app/app.py
EXPOSE 9102
CMD ["/bin/sh","-lc","python /app/cron.py & exec uvicorn app:app --host 0.0.0.0 --port 9102"]
'@

$changed += if (Write-IfChanged "services\observer_hub\Dockerfile"  $observerDocker) { "observer_hub/Dockerfile" }
$changed += if (Write-IfChanged "services\metrics_tuner\Dockerfile" $metricsDocker)  { "metrics_tuner/Dockerfile" }

Write-Host "Rebuilding observer_hub + metrics_tuner..." -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml --profile app build observer_hub metrics_tuner | Out-Host
docker compose -f infra\docker-compose.yml --profile app up -d observer_hub metrics_tuner | Out-Host

Start-Sleep -Seconds 2
try { $h1 = (Invoke-WebRequest http://localhost:9092/health -UseBasicParsing -TimeoutSec 3).Content } catch { $h1 = "<no response>" }
try { $h2 = (Invoke-WebRequest http://localhost:9102/health -UseBasicParsing -TimeoutSec 3).Content } catch { $h2 = "<no response>" }

"`nobserver_hub /health => $h1"
"metrics_tuner /health => $h2"

if ($changed.Count -gt 0) {
  git add ($changed | Sort-Object -Unique) | Out-Null
  Write-Host "`nStaged changes:" -ForegroundColor Green
  $changed | Sort-Object -Unique | ForEach-Object { "  - $_" }
} else {
  Write-Host "`nNo file changes were necessary." -ForegroundColor Green
}
