param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$apiBase = "$backendUrl/api"
$requiredRoutes = @(
    "/api/agent/tasks",
    "/api/tasks/{task_id}/events",
    "/api/sessions/{session_id}/inquiry-tasks",
    "/api/assistant/tasks"
)
$allReady = $true

Write-Host "Docker containers" -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker ps --filter "name=report-mysql" --filter "name=agents-es" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}
else {
    Write-Host "  Docker command unavailable" -ForegroundColor Red
    $allReady = $false
}

Write-Host "Backend" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod "$apiBase/health" -TimeoutSec 3
    $schema = Invoke-RestMethod "$backendUrl/openapi.json" -TimeoutSec 3
    $routes = @($schema.paths.PSObject.Properties.Name)
    $missing = @($requiredRoutes | Where-Object { $routes -notcontains $_ })
    Write-Host "  status=$($health.backend_status), database=$($health.database_connected), es=$($health.es_connected), llm=$($health.llm_enabled)"
    if ($missing.Count -gt 0) {
        Write-Host "  incompatible backend; missing: $($missing -join ', ')" -ForegroundColor Red
        $allReady = $false
    }
    else {
        Write-Host "  asynchronous task and context assistant APIs compatible" -ForegroundColor Green
    }
}
catch {
    Write-Host "  unavailable: $($_.Exception.Message)" -ForegroundColor Red
    $allReady = $false
}

Write-Host "Frontend" -ForegroundColor Cyan
try {
    Invoke-WebRequest $frontendUrl -UseBasicParsing -TimeoutSec 3 | Out-Null
    Write-Host "  ready: $frontendUrl" -ForegroundColor Green
}
catch {
    Write-Host "  unavailable: $frontendUrl" -ForegroundColor Red
    $allReady = $false
}

if ($allReady) {
    Write-Host "Project status: READY" -ForegroundColor Green
    exit 0
}
Write-Host "Project status: NEEDS ATTENTION" -ForegroundColor Yellow
exit 1
