param(
    [string]$ProjectName = "aviation-clean-verify",
    [int]$MySqlPort = 13316,
    [int]$EsPort = 19211,
    [int]$BackendPort = 18010,
    [int]$FrontendPort = 15183,
    [switch]$KeepContainers,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "deploy\docker-compose.yml"
$tempDir = Join-Path $projectRoot ".tmp\clean-deployment"
$envPath = Join-Path $tempDir "$ProjectName.env"
$exampleOutput = Join-Path $tempDir "$ProjectName-examples"
$reportDir = Join-Path $projectRoot "outputs\deployment_validation"
$backendPython = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$appPassword = "verify_" + [guid]::NewGuid().ToString("N").Substring(0, 16)
$rootPassword = "root_" + [guid]::NewGuid().ToString("N").Substring(0, 16)
$started = $false

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose --project-name $ProjectName --env-file $envPath -f $composeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
}

function Wait-Http {
    param([string]$Url, [int]$TimeoutSeconds = 300)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { return }
        }
        catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Url"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker CLI was not found." }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine is not running." }
if (-not (Test-Path -LiteralPath $backendPython)) { throw "Backend virtual environment not found: $backendPython" }

New-Item -ItemType Directory -Force -Path $tempDir, $reportDir | Out-Null
@"
MYSQL_ROOT_PASSWORD=$rootPassword
MYSQL_DATABASE=agents
MYSQL_APP_USER=agents_app
MYSQL_APP_PASSWORD=$appPassword
COMPOSE_CONTAINER_PREFIX=$ProjectName
MYSQL_HOST_PORT=$MySqlPort
ES_HOST_PORT=$EsPort
BACKEND_PORT=$BackendPort
FRONTEND_PORT=$FrontendPort
PUBLIC_API_BASE=http://127.0.0.1:$BackendPort/api
CORS_ORIGINS=["http://127.0.0.1:$FrontendPort","http://localhost:$FrontendPort"]
LLM_ENABLED=false
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT=60
"@ | Set-Content -Encoding UTF8 $envPath

$startedAt = (Get-Date).ToUniversalTime()
try {
    Write-Host "[1/7] Parsing isolated Compose configuration..." -ForegroundColor Cyan
    Invoke-Compose @("config", "--quiet")

    Write-Host "[2/7] Building and starting isolated containers..." -ForegroundColor Cyan
    $upArgs = @("up", "-d")
    if (-not $SkipBuild) { $upArgs += "--build" }
    Invoke-Compose $upArgs
    $started = $true

    Write-Host "[3/7] Waiting for backend and frontend..." -ForegroundColor Cyan
    Wait-Http "http://127.0.0.1:$BackendPort/api/health"
    Wait-Http "http://127.0.0.1:$FrontendPort/healthz"

    Write-Host "[4/7] Seeding MySQL and rebuilding Elasticsearch..." -ForegroundColor Cyan
    Invoke-Compose @("exec", "-T", "backend", "python", "-m", "app.db.seed")
    Invoke-Compose @("exec", "-T", "backend", "python", "-m", "app.rag.pipeline")

    Write-Host "[5/7] Running keyless engineering verification..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "reviewer_verify.ps1") -Mode engineering `
        -ApiBase "http://127.0.0.1:$BackendPort/api" `
        -EsUrl "http://127.0.0.1:$EsPort"
    if ($LASTEXITCODE -ne 0) { throw "Reviewer engineering verification failed." }

    Write-Host "[6/7] Running three complete learner flows..." -ForegroundColor Cyan
    if (Test-Path -LiteralPath $exampleOutput) { Remove-Item -LiteralPath $exampleOutput -Recurse -Force }
    Push-Location (Join-Path $projectRoot "backend")
    try {
        & $backendPython -m app.evaluation.submission_examples_runner `
            --api-base "http://127.0.0.1:$BackendPort/api" `
            --output-dir $exampleOutput
        if ($LASTEXITCODE -ne 0) { throw "Complete learner flows failed." }
    }
    finally {
        Pop-Location
    }

    Write-Host "[7/7] Verifying persisted records and writing report..." -ForegroundColor Cyan
    $sql = "SELECT CONCAT('diagnosis=',COUNT(*)) FROM diagnosis_records; SELECT CONCAT('sessions=',COUNT(*)) FROM agent_sessions; SELECT CONCAT('steps=',COUNT(*)) FROM agent_steps; SELECT CONCAT('resources=',COUNT(*)) FROM generated_resources; SELECT CONCAT('reports=',COUNT(*)) FROM learning_reports;"
    $counts = & docker compose --project-name $ProjectName --env-file $envPath -f $composeFile `
        exec -T -e "MYSQL_PWD=$appPassword" mysql mysql -N -uagents_app agents -e $sql
    if ($LASTEXITCODE -ne 0) { throw "MySQL persistence verification failed." }

    $health = Invoke-RestMethod "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 10
    $esCount = Invoke-RestMethod "http://127.0.0.1:$EsPort/aviation_material_knowledge/_count" -TimeoutSec 10
    $examples = @(Get-ChildItem -LiteralPath $exampleOutput -Filter "*_complete_example.json")
    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        started_at = $startedAt.ToString("o")
        project_name = $ProjectName
        status = "passed"
        isolated_from_existing_data = $true
        llm_key_required = $false
        health = [ordered]@{
            database_connected = $health.database_connected
            es_connected = $health.es_connected
            knowledge_source = $health.knowledge_source
            version = $health.version
        }
        es_document_count = [int]$esCount.count
        complete_example_count = $examples.Count
        mysql_counts = @($counts)
        containers_kept = [bool]$KeepContainers
    }
    $jsonPath = Join-Path $reportDir "clean_deployment_latest.json"
    $mdPath = Join-Path $reportDir "clean_deployment_latest.md"
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonPath
    @(
        "# Clean deployment verification",
        "",
        "- Result: **PASS**",
        "- Isolated Compose project: ``$ProjectName``",
        "- LLM API key required: **No**",
        "- MySQL connected: ``$($health.database_connected)``",
        "- Elasticsearch connected: ``$($health.es_connected)``",
        "- ES documents: ``$($esCount.count)``",
        "- Complete learner flows: ``$($examples.Count)``",
        "- Persisted records: ``$($counts -join ', ')``",
        "",
        "> The verification used independent containers, ports, credentials and Docker volumes."
    ) -join "`n" | Set-Content -Encoding UTF8 $mdPath
    Write-Host "Clean deployment verification passed." -ForegroundColor Green
    Write-Host "  Report: $mdPath"
}
finally {
    if ($started -and -not $KeepContainers) {
        Write-Host "Cleaning isolated containers and volumes..." -ForegroundColor Yellow
        try { Invoke-Compose @("down", "-v", "--remove-orphans") } catch { Write-Warning $_ }
    }
    if (-not $KeepContainers -and (Test-Path -LiteralPath $envPath)) {
        Remove-Item -LiteralPath $envPath -Force
    }
}
