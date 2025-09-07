param(
  [int]$TimeoutSec = 3
)

$ErrorActionPreference = 'Stop'

function Get-OrchestratorPort {
  try {
    $line = docker port infra-orchestrator-1 8080 | Select-String '0\.0\.0\.0:' | Select-Object -First 1
    if ($line) { return ($line.ToString() -split ':')[-1].Trim() }
  } catch {}
  return 8080
}

function Test-Url([string]$Url, [int]$Timeout=$TimeoutSec) {
  try {
    $resp = Invoke-RestMethod -UseBasicParsing -TimeoutSec $Timeout -Uri $Url
    Write-Host "OK  $Url -> $(($resp | ConvertTo-Json -Compress))" -ForegroundColor Green
    return $true
  } catch {
    Write-Host "FAIL $Url -> $($_.Exception.Message)" -ForegroundColor Red
    return $false
  }
}

Write-Host "== Host-side checks ==" -ForegroundColor Cyan
$orchPort = Get-OrchestratorPort
$ok = $true
$ok = (Test-Url "http://localhost:$orchPort/health") -and $ok
$ok = (Test-Url "http://localhost:$orchPort/ready")  -and $ok
$ok = (Test-Url "http://localhost:9092/health")      -and $ok
$ok = (Test-Url "http://localhost:9102/health")      -and $ok

Write-Host "`n== In-network checks (curl image) ==" -ForegroundColor Cyan
$curl = 'curlimages/curl'
try { docker image inspect $curl *>$null } catch { docker pull $curl *>$null | Out-Null }

$netOk = $true
$netOk = (docker run --rm --network foundry_net $curl -fsS http://observer_hub:9092/health; if ($LASTEXITCODE -eq 0) { Write-Host "OK  observer_hub" -ForegroundColor Green; $true } else { Write-Host "FAIL observer_hub" -ForegroundColor Red; $false }) -and $netOk
$netOk = (docker run --rm --network foundry_net $curl -fsS http://metrics_tuner:9102/health; if ($LASTEXITCODE -eq 0) { Write-Host "OK  metrics_tuner" -ForegroundColor Green; $true } else { Write-Host "FAIL metrics_tuner" -ForegroundColor Red; $false }) -and $netOk

if ($ok -and $netOk) { exit 0 } else { exit 1 }
