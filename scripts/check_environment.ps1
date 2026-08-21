$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$checks = @()

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $script:checks += [pscustomobject]@{
        Check = $Name
        Status = if ($Passed) { "PASS" } else { "FAIL" }
        Detail = $Detail
    }
}

Add-Check "Backend venv" (Test-Path "$projectRoot\backend\.venv\Scripts\python.exe") "$projectRoot\backend\.venv"
Add-Check "Frontend dependencies" (Test-Path "$projectRoot\frontend\node_modules") "$projectRoot\frontend\node_modules"
Add-Check "Backend .env" (Test-Path "$projectRoot\backend\.env") "$projectRoot\backend\.env"

$dockerReady = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info *> $null
    $dockerReady = $LASTEXITCODE -eq 0
}
Add-Check "Docker Engine" $dockerReady "Docker Desktop must be running"

if ($dockerReady) {
    foreach ($container in @("report-mysql", "agents-es")) {
        $running = docker ps --filter "name=^/$container$" --format "{{.Names}}"
        Add-Check "Container $container" ($running -eq $container) "Use: docker start $container"
    }
}

try {
    $health = Invoke-RestMethod "http://127.0.0.1:8000/api/health" -TimeoutSec 3
    Add-Check "Backend API" $true "version=$($health.version)"
    Add-Check "MySQL connection" ([bool]$health.database_connected) "data_backend=$($health.data_backend)"
    Add-Check "Elasticsearch connection" ([bool]$health.es_connected) "source=$($health.knowledge_source)"
}
catch {
    Add-Check "Backend API" $false "Start backend on port 8000"
}

try {
    Invoke-WebRequest "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 3 | Out-Null
    Add-Check "Frontend" $true "http://127.0.0.1:5173"
}
catch {
    Add-Check "Frontend" $false "Start Vite on port 5173"
}

$checks | Format-Table -AutoSize
if ($checks.Status -contains "FAIL") { exit 1 }
exit 0
