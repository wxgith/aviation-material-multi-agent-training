param([switch]$StopDocker)

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $projectRoot ".tmp\project-processes.json"

function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

if (Test-Path $statePath) {
    $state = Get-Content -Raw -Encoding UTF8 $statePath | ConvertFrom-Json
    foreach ($property in @("frontend_process_id", "backend_process_id")) {
        $processId = [int]($state.$property)
        if ($processId -gt 0 -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
            Write-Host "Stopping process tree $processId..."
            Stop-ProcessTree -ProcessId $processId
        }
    }
    Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
    Write-Host "Project processes started by start_project.ps1 were stopped." -ForegroundColor Green
}
else {
    Write-Host "No recorded project process file found. Existing manually started terminals were not changed." -ForegroundColor Yellow
}

if ($StopDocker) {
    foreach ($container in @("agents-es", "report-mysql")) {
        $running = docker ps --filter "name=^/$container$" --format "{{.Names}}" 2>$null
        if ($running -eq $container) {
            docker stop $container | Out-Null
            Write-Host "Stopped Docker container: $container"
        }
    }
}
else {
    Write-Host "Docker containers remain running. Use -StopDocker only when you want to stop them too."
}
