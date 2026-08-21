param(
    [switch]$SkipDocker,
    [switch]$NoBrowser,
    [switch]$Headless,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$DockerWaitSeconds = 120
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$stateDir = Join-Path $projectRoot ".tmp"
$statePath = Join-Path $stateDir "project-processes.json"
$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$apiBase = "$backendUrl/api"
$requiredRoutes = @(
    "/api/health",
    "/api/agent/tasks",
    "/api/tasks/{task_id}/events",
    "/api/sessions",
    "/api/sessions/{session_id}/inquiry-tasks",
    "/api/assistant/tasks"
)

function Test-HttpEndpoint {
    param([string]$Url, [int]$TimeoutSec = 2)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-BackendCapabilities {
    param([string]$BaseUrl)
    try {
        $schema = Invoke-RestMethod "$BaseUrl/openapi.json" -TimeoutSec 3
        $availableRoutes = @($schema.paths.PSObject.Properties.Name)
        foreach ($route in $requiredRoutes) {
            if ($availableRoutes -notcontains $route) { return $false }
        }
        return $true
    }
    catch {
        return $false
    }
}

function Test-DockerEngine {
    # PowerShell 5 treats Docker's connection message on stderr as a terminating
    # NativeCommandError when ErrorActionPreference is Stop. cmd.exe keeps this
    # readiness probe quiet so the script can show a useful recovery message.
    & cmd.exe /d /c "docker info >nul 2>&1"
    return $LASTEXITCODE -eq 0
}

function Start-DockerEngine {
    Write-Host "Docker Engine is not ready. Starting Docker Desktop..." -ForegroundColor Yellow

    & cmd.exe /d /c "docker desktop start >nul 2>&1"
    if ($LASTEXITCODE -ne 0) {
        $dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        if (-not (Test-Path -LiteralPath $dockerDesktop)) {
            throw @"
Docker Engine is not running and Docker Desktop could not be started automatically.
Open Docker Desktop manually, wait until it reports Running, then run:
  cd $projectRoot
  .\scripts\start_project.ps1
"@
        }
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
    }

    Write-Host "Waiting for Docker Engine (up to $DockerWaitSeconds seconds)" -NoNewline
    for ($elapsed = 0; $elapsed -lt $DockerWaitSeconds; $elapsed += 2) {
        if (Test-DockerEngine) {
            Write-Host " ready." -ForegroundColor Green
            return
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }

    Write-Host ""
    throw @"
Docker Desktop did not become ready within $DockerWaitSeconds seconds.
Open Docker Desktop and check whether the Linux engine reports Running, then retry.
If Docker is intentionally unavailable, switch backend/.env to JSON fallback mode and run with -SkipDocker.
"@
}

function Start-ServerWindow {
    param(
        [string]$WorkingDirectory,
        [string]$Command
    )
    $arguments = @("-NoExit", "-NoProfile", "-Command", $Command)
    if ($Headless) {
        return Start-Process powershell.exe -WorkingDirectory $WorkingDirectory -ArgumentList $arguments -WindowStyle Hidden -PassThru
    }
    return Start-Process powershell.exe -WorkingDirectory $WorkingDirectory -ArgumentList $arguments -PassThru
}

Write-Host "[1/5] Checking project files..." -ForegroundColor Cyan
if (-not (Test-Path $backendPython)) {
    throw "Backend virtual environment not found: $backendPython"
}
if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    throw "Frontend package.json not found."
}
if (-not (Test-Path (Join-Path $backendDir ".env"))) {
    throw "Backend .env not found. Copy .env.example to .env and configure it first."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm.cmd not found. Install Node.js or load the project runtime first."
}

if (-not $SkipDocker) {
    Write-Host "[2/5] Checking Docker containers..." -ForegroundColor Cyan
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker command not found. Start Docker Desktop and retry."
    }
    if (-not (Test-DockerEngine)) {
        Start-DockerEngine
    }
    foreach ($container in @("report-mysql", "agents-es")) {
        $exists = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
        if ($exists -ne $container) {
            throw "Required Docker container not found: $container"
        }
        $running = docker ps --filter "name=^/$container$" --format "{{.Names}}"
        if ($running -ne $container) {
            Write-Host "Starting $container..."
            docker start $container | Out-Null
        }
    }
}

Write-Host "[3/5] Checking occupied service ports..." -ForegroundColor Cyan
$backendAlreadyRunning = Test-HttpEndpoint "$apiBase/health"
if ($backendAlreadyRunning -and -not (Test-BackendCapabilities $backendUrl)) {
    throw @"
Port $BackendPort is serving an older or incompatible backend.
Close the old backend PowerShell window with Ctrl+C, then run this command again.
The current backend must expose /api/agent/tasks, /api/assistant/tasks and the task event endpoints.
"@
}

$frontendAlreadyRunning = Test-HttpEndpoint $frontendUrl
$backendProcess = $null
$frontendProcess = $null

Write-Host "[4/5] Starting backend and frontend..." -ForegroundColor Cyan
if (-not $backendAlreadyRunning) {
    $backendCommand = "& '$backendPython' -m app.db.migrate; if (`$LASTEXITCODE -ne 0) { throw 'Database migration failed.' }; & '$backendPython' -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BackendPort"
    $backendProcess = Start-ServerWindow -WorkingDirectory $backendDir -Command $backendCommand
}
else {
    Write-Host "Compatible backend is already running on port $BackendPort."
}

if (-not $frontendAlreadyRunning) {
    $frontendCommand = "`$env:VITE_API_BASE='$apiBase'; npm.cmd run dev -- --host 0.0.0.0 --port $FrontendPort --strictPort"
    $frontendProcess = Start-ServerWindow -WorkingDirectory $frontendDir -Command $frontendCommand
}
else {
    Write-Host "Frontend is already running on port $FrontendPort."
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$state = [ordered]@{
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    backend_port = $BackendPort
    frontend_port = $FrontendPort
    backend_process_id = if ($backendProcess) { $backendProcess.Id } else { $null }
    frontend_process_id = if ($frontendProcess) { $frontendProcess.Id } else { $null }
    backend_reused = [bool]$backendAlreadyRunning
    frontend_reused = [bool]$frontendAlreadyRunning
}
$state | ConvertTo-Json | Set-Content -Encoding UTF8 $statePath

Write-Host "[5/5] Waiting for services and running smoke checks..." -ForegroundColor Cyan
$backendReady = $false
$frontendReady = $false
for ($attempt = 1; $attempt -le 45; $attempt++) {
    $backendReady = (Test-HttpEndpoint "$apiBase/health") -and (Test-BackendCapabilities $backendUrl)
    $frontendReady = Test-HttpEndpoint $frontendUrl
    if ($backendReady -and $frontendReady) { break }
    Start-Sleep -Seconds 1
}

if (-not $backendReady -or -not $frontendReady) {
    throw "Services did not become ready in 45 seconds. Run .\scripts\project_status.ps1 and inspect the server windows."
}

$health = Invoke-RestMethod "$apiBase/health" -TimeoutSec 5
$profiles = Invoke-RestMethod "$apiBase/profiles" -TimeoutSec 5
$domains = Invoke-RestMethod "$apiBase/domains" -TimeoutSec 5
if (@($profiles).Count -lt 3 -or @($domains).Count -lt 3) {
    throw "API smoke check failed: expected at least 3 profiles and 3 domains."
}
if ($health.database_enabled -and -not $health.database_connected) {
    throw "MySQL is enabled but not connected. Check Docker and DATABASE_URL."
}
if ($health.es_enabled -and -not $health.es_connected) {
    throw "Elasticsearch is enabled but not connected. Check agents-es and ES_URL."
}

Write-Host "Project is ready." -ForegroundColor Green
Write-Host "  Frontend:  $frontendUrl"
Write-Host "  Health:    $apiBase/health"
Write-Host "  Database:  $($health.database_connected)"
Write-Host "  ES:        $($health.es_connected)"
Write-Host "  Retrieval: $($health.retrieval_mode)"
Write-Host "  LLM:       enabled=$($health.llm_enabled), model=$($health.llm_model)"
Write-Host "  Task API:  compatible"
Write-Host "  Task store: enabled=$($health.async_tasks.persistence_enabled), ready=$($health.async_tasks.table_ready)"

if (-not $NoBrowser) {
    Start-Process $frontendUrl
    Start-Process "$apiBase/health"
}
