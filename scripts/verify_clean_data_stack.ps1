param(
    [string]$ProjectName = "aviation-clean-data",
    [int]$MySqlPort = 13316,
    [int]$EsPort = 19211,
    [int]$BackendPort = 18010,
    [switch]$KeepContainers
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$composeFile = Join-Path $projectRoot "deploy\docker-compose.yml"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$tempDir = Join-Path $projectRoot ".tmp\clean-data-stack"
$envPath = Join-Path $tempDir "$ProjectName.env"
$examplesDir = Join-Path $tempDir "$ProjectName-examples"
$backendLog = Join-Path $tempDir "$ProjectName-backend.log"
$backendErrorLog = Join-Path $tempDir "$ProjectName-backend-error.log"
$reportDir = Join-Path $projectRoot "outputs\deployment_validation"
$appPassword = "verify_" + [guid]::NewGuid().ToString("N").Substring(0, 16)
$rootPassword = "root_" + [guid]::NewGuid().ToString("N").Substring(0, 16)
$backendProcess = $null
$started = $false
$originalEnv = @{}

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose --project-name $ProjectName --env-file $envPath -f $composeFile @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed: $($Arguments -join ' ')" }
}

function Wait-Http {
    param([string]$Url, [int]$TimeoutSeconds = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { return }
        }
        catch { Start-Sleep -Seconds 2 }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Url"
}

function Set-TemporaryEnvironment {
    param([hashtable]$Values)
    foreach ($key in $Values.Keys) {
        $script:originalEnv[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
        [Environment]::SetEnvironmentVariable($key, [string]$Values[$key], "Process")
    }
}

function Restore-Environment {
    foreach ($key in $script:originalEnv.Keys) {
        [Environment]::SetEnvironmentVariable($key, $script:originalEnv[$key], "Process")
    }
}

if (-not (Test-Path -LiteralPath $python)) { throw "Backend virtual environment not found: $python" }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine is not running." }

New-Item -ItemType Directory -Force -Path $tempDir, $reportDir | Out-Null
@"
MYSQL_ROOT_PASSWORD=$rootPassword
MYSQL_DATABASE=agents
MYSQL_APP_USER=agents_app
MYSQL_APP_PASSWORD=$appPassword
COMPOSE_CONTAINER_PREFIX=$ProjectName
MYSQL_HOST_PORT=$MySqlPort
ES_HOST_PORT=$EsPort
BACKEND_PORT=18011
FRONTEND_PORT=15184
PUBLIC_API_BASE=http://127.0.0.1:18011/api
CORS_ORIGINS=["http://127.0.0.1:15184"]
LLM_ENABLED=false
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT=60
"@ | Set-Content -Encoding UTF8 $envPath

try {
    Write-Host "[1/7] Starting fresh MySQL and Elasticsearch volumes..." -ForegroundColor Cyan
    Invoke-Compose @("up", "-d", "mysql", "elasticsearch")
    $started = $true
    Wait-Http "http://127.0.0.1:$EsPort/_cluster/health"

    $environment = @{
        APP_ENV = "clean-verification"
        DATA_BACKEND = "sql"
        DATABASE_ENABLED = "true"
        DATABASE_URL = "mysql+pymysql://agents_app:$appPassword@127.0.0.1:$MySqlPort/agents"
        ES_ENABLED = "true"
        ES_URL = "http://127.0.0.1:$EsPort"
        ES_USERNAME = ""
        ES_PASSWORD = ""
        ES_INDEX_KNOWLEDGE = "aviation_material_knowledge"
        BGE_ENABLED = "false"
        EMBEDDING_BACKEND = "none"
        RETRIEVAL_MODE = "hybrid"
        LLM_ENABLED = "false"
        LLM_BASE_URL = ""
        LLM_API_KEY = ""
        LLM_MODEL = ""
    }
    Set-TemporaryEnvironment $environment

    Write-Host "[2/7] Migrating and seeding a fresh SQL schema..." -ForegroundColor Cyan
    Push-Location $backendDir
    try {
        $seeded = $false
        for ($attempt = 1; $attempt -le 20 -and -not $seeded; $attempt++) {
            & $python -m app.db.migrate
            if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 3; continue }
            & $python -m app.db.seed
            if ($LASTEXITCODE -eq 0) { $seeded = $true } else { Start-Sleep -Seconds 3 }
        }
        if (-not $seeded) { throw "MySQL seed did not become ready." }

        Write-Host "[3/7] Rebuilding the full RAG index..." -ForegroundColor Cyan
        & $python -m app.rag.pipeline
        if ($LASTEXITCODE -ne 0) { throw "RAG pipeline failed." }
    }
    finally { Pop-Location }

    Write-Host "[4/7] Starting the host FastAPI process against the clean data stack..." -ForegroundColor Cyan
    $backendProcess = Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog
    Wait-Http "http://127.0.0.1:$BackendPort/api/health"

    Write-Host "[5/7] Verifying engineering status and three complete learner flows..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "reviewer_verify.ps1") -Mode engineering `
        -ApiBase "http://127.0.0.1:$BackendPort/api" -EsUrl "http://127.0.0.1:$EsPort"
    if ($LASTEXITCODE -ne 0) { throw "Engineering verification failed." }
    if (Test-Path -LiteralPath $examplesDir) { Remove-Item -LiteralPath $examplesDir -Recurse -Force }
    Push-Location $backendDir
    try {
        & $python -m app.evaluation.submission_examples_runner `
            --api-base "http://127.0.0.1:$BackendPort/api" --output-dir $examplesDir
        if ($LASTEXITCODE -ne 0) { throw "Three complete learner flows failed." }
    }
    finally { Pop-Location }

    Write-Host "[6/7] Building the frontend production bundle..." -ForegroundColor Cyan
    Push-Location $frontendDir
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
    }
    finally { Pop-Location }

    Write-Host "[7/7] Verifying persisted SQL records and writing evidence..." -ForegroundColor Cyan
    $sql = "SELECT CONCAT('diagnosis=',COUNT(*)) FROM diagnosis_records; SELECT CONCAT('sessions=',COUNT(*)) FROM agent_sessions; SELECT CONCAT('steps=',COUNT(*)) FROM agent_steps; SELECT CONCAT('resources=',COUNT(*)) FROM generated_resources; SELECT CONCAT('reports=',COUNT(*)) FROM learning_reports;"
    $counts = & docker compose --project-name $ProjectName --env-file $envPath -f $composeFile `
        exec -T -e "MYSQL_PWD=$appPassword" mysql mysql -N -uagents_app agents -e $sql
    if ($LASTEXITCODE -ne 0) { throw "SQL record count failed." }
    $health = Invoke-RestMethod "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 10
    $esCount = Invoke-RestMethod "http://127.0.0.1:$EsPort/aviation_material_knowledge/_count" -TimeoutSec 10
    $exampleCount = @(Get-ChildItem -LiteralPath $examplesDir -Filter "*_complete_example.json").Count
    if ($exampleCount -ne 3) { throw "Expected three complete examples, found $exampleCount." }
    if ([int]$esCount.count -ne 1766) { throw "Expected 1766 ES documents, found $($esCount.count)." }

    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        status = "passed"
        mode = "host application plus isolated Docker data stack"
        llm_key_required = $false
        independent_ports = @{ mysql = $MySqlPort; elasticsearch = $EsPort; backend = $BackendPort }
        database_connected = $health.database_connected
        es_connected = $health.es_connected
        knowledge_source = $health.knowledge_source
        es_document_count = [int]$esCount.count
        complete_learner_flows = $exampleCount
        mysql_counts = @($counts)
        frontend_build = "passed"
    }
    $jsonPath = Join-Path $reportDir "clean_data_stack_latest.json"
    $mdPath = Join-Path $reportDir "clean_data_stack_latest.md"
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonPath
    @(
        "# Isolated data-stack verification",
        "",
        "- Result: **PASS**",
        "- Mode: host application plus isolated MySQL/Elasticsearch containers and volumes",
        "- LLM API key required: **No**",
        "- Elasticsearch documents: $($esCount.count)",
        "- Complete learner flows: $exampleCount",
        "- Frontend production build: PASS",
        "- SQL records: $($counts -join '; ')",
        "",
        "> The verification did not read or modify report-mysql, agents-es or their volumes."
    ) -join "`n" | Set-Content -Encoding UTF8 $mdPath
    Write-Host "Clean data-stack verification passed." -ForegroundColor Green
    Write-Host "  Report: $mdPath"
}
finally {
    if ($backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -Force }
    Restore-Environment
    if ($started -and -not $KeepContainers) {
        try { Invoke-Compose @("down", "-v", "--remove-orphans") } catch { Write-Warning $_ }
    }
    if (-not $KeepContainers -and (Test-Path -LiteralPath $envPath)) { Remove-Item -LiteralPath $envPath -Force }
}
