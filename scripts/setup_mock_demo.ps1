param(
    [switch]$NoBrowser,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$envPath = Join-Path $backendDir ".env"
$envExample = Join-Path $backendDir ".env.example"

Write-Host "Aviation material training system - portable setup" -ForegroundColor Cyan
Write-Host "This mode does not require Docker, MySQL, Elasticsearch, or an API key."

if (-not (Get-Command py.exe -ErrorAction SilentlyContinue) -and -not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 was not found. Install Python 3.11 and reopen PowerShell."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 20 LTS and reopen PowerShell."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "[1/4] Creating Python virtual environment..." -ForegroundColor Cyan
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        & py.exe -3.11 -m venv (Join-Path $backendDir ".venv")
    }
    else {
        & python.exe -m venv (Join-Path $backendDir ".venv")
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python virtual environment." }
}
else {
    Write-Host "[1/4] Python virtual environment already exists." -ForegroundColor DarkGray
}

Write-Host "[2/4] Checking backend dependencies..." -ForegroundColor Cyan
& $venvPython -c "import fastapi, uvicorn, pydantic, httpx, sqlalchemy, elasticsearch" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed. Check the network and Python package source." }
}

Write-Host "[3/4] Checking frontend dependencies..." -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules\.package-lock.json"))) {
    Push-Location $frontendDir
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed. Check the network and npm source." }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Host "[4/4] Creating JSON/mock configuration..." -ForegroundColor Cyan
    Copy-Item -LiteralPath $envExample -Destination $envPath
}
else {
    Write-Host "[4/4] Existing backend/.env retained." -ForegroundColor DarkGray
}

if ($SetupOnly) {
    Write-Host "Setup completed. Run .\scripts\start_project.ps1 -SkipDocker to start." -ForegroundColor Green
    exit 0
}

$startArgs = @{ SkipDocker = $true }
if ($NoBrowser) { $startArgs.NoBrowser = $true }
& (Join-Path $PSScriptRoot "start_project.ps1") @startArgs
