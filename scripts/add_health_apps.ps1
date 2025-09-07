# scripts/add_health_apps.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Dir($p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null } }

function Ensure-LinesInFile {
    param(
        [Parameter(Mandatory)] [string] $Path,
        [Parameter(Mandatory)] [string[]] $Lines
    )
    if (-not (Test-Path $Path)) {
        Ensure-Dir (Split-Path $Path)
        Set-Content -Path $Path -Value ($Lines -join "`r`n") -NoNewline
        return $true
    }
    $orig = Get-Content -Raw -Path $Path
    $lower = ($orig -split "`r?`n") | ForEach-Object { $_.Trim().ToLowerInvariant() }
    $missing = @()
    foreach ($l in $Lines) {
        if (-not ($lower -contains ($l.Trim().ToLowerInvariant()))) {
            $missing += $l
        }
    }
    if ($missing.Count -gt 0) {
        Add-Content -Path $Path -Value "`r`n$($missing -join "`r`n")"
        return $true
    }
    return $false
}

function Ensure-HealthApp {
    param(
        [Parameter(Mandatory)] [string] $Service,
        [Parameter(Mandatory)] [ValidateSet("observer_hub","metrics_tuner")] [string] $Kind
    )

    $svcDir = Join-Path "services" $Service
    $appPy  = Join-Path $svcDir "app.py"
    Ensure-Dir $svcDir

    if ($Kind -eq "observer_hub") {
        $content = @'
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
'@
    } else {
        $content = @'
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
        if callable(fn):
            fn()
        else:
            while True:
                time.sleep(60)
    except Exception:
        # keep health responsive even if background work fails
        while True:
            time.sleep(60)

t = threading.Thread(target=_bg, daemon=True)
t.start()
'@
    }

    $wrote = $false
    if (-not (Test-Path $appPy)) {
        Set-Content -Path $appPy -Value $content -NoNewline
        $wrote = $true
    } else {
        $raw = Get-Content -Raw -Path $appPy
        if ($raw -notmatch '(?ms)@app\.get\(\"/health\"\)') {
            Add-Content -Path $appPy -Value "`r`n`r`n" + $content
            $wrote = $true
        }
    }

    $req = Join-Path $svcDir "requirements.txt"
    $reqChanged = Ensure-LinesInFile -Path $req -Lines @("fastapi","uvicorn")

    [PSCustomObject]@{
        service     = $Service
        app_written = $wrote
        req_updated = $reqChanged
        app_path    = $appPy
        req_path    = $req
    }
}

Write-Host "Adding minimal /health apps..." -ForegroundColor Cyan
$results = @()
$results += (Ensure-HealthApp -Service "observer_hub"  -Kind "observer_hub")
$results += (Ensure-HealthApp -Service "metrics_tuner" -Kind "metrics_tuner")

$results | Format-Table -AutoSize

Write-Host "`nDone. Next steps:" -ForegroundColor Green
Write-Host "  1) Rebuild the two services:"
Write-Host "     docker compose -f infra\docker-compose.yml --profile app build observer_hub metrics_tuner"
Write-Host "     docker compose -f infra\docker-compose.yml --profile app up -d observer_hub metrics_tuner"
Write-Host "  2) Verify:"
Write-Host "     curl http://localhost:9092/health"
Write-Host "     curl http://localhost:9102/health"
Write-Host "  3) Commit:"
Write-Host "     git add services\observer_hub\app.py services\metrics_tuner\app.py services\observer_hub\requirements.txt services\metrics_tuner\requirements.txt"
Write-Host "     git commit -m `"feat: add minimal /health apps for observer_hub and metrics_tuner`""
