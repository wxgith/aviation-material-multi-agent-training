param(
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [string]$ProjectName = "aviation-restore-verify",
    [int]$MySqlPort = 13317,
    [int]$EsPort = 19212
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "deploy\docker-compose.yml"
$tempDir = Join-Path $projectRoot ".tmp\restore-verification"
$envPath = Join-Path $tempDir "$ProjectName.env"
$reportDir = Join-Path $projectRoot "outputs\deployment_validation"
$resolvedBackup = (Resolve-Path -LiteralPath $BackupDir).Path
$manifest = Get-Content -Raw -Encoding UTF8 (Join-Path $resolvedBackup "BACKUP_MANIFEST.json") | ConvertFrom-Json
$appPassword = "verify_" + [guid]::NewGuid().ToString("N").Substring(0, 16)
$rootPassword = "root_" + [guid]::NewGuid().ToString("N").Substring(0, 16)
$started = $false

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

New-Item -ItemType Directory -Force -Path $tempDir, $reportDir | Out-Null
@"
MYSQL_ROOT_PASSWORD=$rootPassword
MYSQL_DATABASE=agents
MYSQL_APP_USER=agents_app
MYSQL_APP_PASSWORD=$appPassword
COMPOSE_CONTAINER_PREFIX=$ProjectName
MYSQL_HOST_PORT=$MySqlPort
ES_HOST_PORT=$EsPort
BACKEND_PORT=18012
FRONTEND_PORT=15185
PUBLIC_API_BASE=http://127.0.0.1:18012/api
CORS_ORIGINS=["http://127.0.0.1:15185"]
LLM_ENABLED=false
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT=60
"@ | Set-Content -Encoding UTF8 $envPath

try {
    Write-Host "[1/4] Starting empty MySQL and Elasticsearch volumes..." -ForegroundColor Cyan
    Invoke-Compose @("up", "-d", "mysql", "elasticsearch")
    $started = $true
    Wait-Http "http://127.0.0.1:$EsPort/_cluster/health"

    Write-Host "[2/4] Restoring the backup into the isolated stack..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "restore_data.ps1") -BackupDir $resolvedBackup `
        -MySqlContainer "$ProjectName-mysql" -MySqlDatabase "agents" `
        -EsUrl "http://127.0.0.1:$EsPort" -EsIndex "aviation_material_knowledge" -Force
    if ($LASTEXITCODE -ne 0) { throw "Restore command failed." }

    Write-Host "[3/4] Comparing SQL table counts and ES document count..." -ForegroundColor Cyan
    $mismatches = @()
    foreach ($property in $manifest.mysql_table_counts.PSObject.Properties) {
        $table = $property.Name
        if ($table -notmatch "^[A-Za-z0-9_]+$") { throw "Unsafe table name in manifest: $table" }
        $actual = & docker compose --project-name $ProjectName --env-file $envPath -f $composeFile `
            exec -T -e "MYSQL_PWD=$appPassword" mysql mysql -N -uagents_app agents `
            -e "SELECT COUNT(*) FROM $table"
        if ($LASTEXITCODE -ne 0) { throw "Could not count restored table: $table" }
        if ([int]$actual -ne [int]$property.Value) {
            $mismatches += "$table expected=$($property.Value) actual=$actual"
        }
    }
    $esCount = Invoke-RestMethod "http://127.0.0.1:$EsPort/aviation_material_knowledge/_count" -TimeoutSec 15
    if ([int]$esCount.count -ne [int]$manifest.es_document_count) {
        $mismatches += "Elasticsearch expected=$($manifest.es_document_count) actual=$($esCount.count)"
    }
    if ($mismatches.Count -gt 0) { throw "Restore mismatch: $($mismatches -join '; ')" }

    Write-Host "[4/4] Writing restore verification evidence..." -ForegroundColor Cyan
    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        status = "passed"
        backup = $resolvedBackup
        isolated_restore = $true
        mysql_table_counts = $manifest.mysql_table_counts
        es_document_count = [int]$esCount.count
    }
    $tableCount = @($manifest.mysql_table_counts.PSObject.Properties).Count
    $jsonPath = Join-Path $reportDir "backup_restore_latest.json"
    $mdPath = Join-Path $reportDir "backup_restore_latest.md"
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonPath
    @(
        "# Backup and restore verification",
        "",
        "- Result: **PASS**",
        "- Isolated restore: **Yes**",
        "- Elasticsearch documents: $($esCount.count)",
        "- SQL tables checked: $tableCount",
        "",
        "> The source MySQL and Elasticsearch services were not modified."
    ) -join "`n" | Set-Content -Encoding UTF8 $mdPath
    Write-Host "Backup restore verification passed." -ForegroundColor Green
    Write-Host "  Report: $mdPath"
}
finally {
    if ($started) {
        try { Invoke-Compose @("down", "-v", "--remove-orphans") } catch { Write-Warning $_ }
    }
    if (Test-Path -LiteralPath $envPath) { Remove-Item -LiteralPath $envPath -Force }
}
