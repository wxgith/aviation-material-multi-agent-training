param(
    [string]$OutputRoot = "",
    [string]$MySqlContainer = "report-mysql",
    [string]$MySqlDatabase = "agents",
    [string]$EsUrl = "http://127.0.0.1:9201",
    [string]$EsIndex = "aviation_material_knowledge"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
if (-not $OutputRoot) { $OutputRoot = Join-Path $projectRoot "backups" }
if ($MySqlDatabase -notmatch "^[A-Za-z0-9_]+$") { throw "Unsafe MySQL database name." }
if (-not (Test-Path -LiteralPath $python)) { throw "Backend Python was not found: $python" }

$running = docker ps --filter "name=^/$MySqlContainer$" --format "{{.Names}}"
if ($running -ne $MySqlContainer) { throw "MySQL container is not running: $MySqlContainer" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $OutputRoot "aviation-training-$stamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$sqlName = "mysql-$MySqlDatabase.sql"
$sqlPath = Join-Path $backupDir $sqlName
$containerPath = "/tmp/$sqlName"
$esPath = Join-Path $backupDir "elasticsearch-$EsIndex.ndjson"
$tables = @(
    "learners", "diagnosis_records", "agent_sessions", "agent_steps",
    "generated_resources", "learning_reports", "feedback_records", "learning_interactions",
    "async_tasks"
)
$containerEnv = docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $MySqlContainer
$rootLine = $containerEnv | Where-Object { $_ -like "MYSQL_ROOT_PASSWORD=*" } | Select-Object -First 1
if (-not $rootLine) { throw "MYSQL_ROOT_PASSWORD was not found in container configuration." }
$rootPassword = $rootLine.Substring("MYSQL_ROOT_PASSWORD=".Length)

Write-Host "[1/4] Exporting MySQL with mysqldump..." -ForegroundColor Cyan
docker exec -e "MYSQL_PWD=$rootPassword" $MySqlContainer sh -c `
    "mysqldump --single-transaction --routines --triggers --set-gtid-purged=OFF -uroot $MySqlDatabase > $containerPath"
if ($LASTEXITCODE -ne 0) { throw "mysqldump failed." }
docker cp "${MySqlContainer}:$containerPath" $sqlPath | Out-Null
docker exec $MySqlContainer rm -f $containerPath | Out-Null
if (-not (Test-Path -LiteralPath $sqlPath) -or (Get-Item $sqlPath).Length -lt 1000) { throw "MySQL dump is incomplete." }

Write-Host "[2/4] Exporting Elasticsearch as NDJSON..." -ForegroundColor Cyan
Push-Location (Join-Path $projectRoot "backend")
try {
    $esExport = & $python -m app.ops.es_archive export --url $EsUrl --index $EsIndex --file $esPath | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Elasticsearch export failed." }
}
finally { Pop-Location }

$tableCounts = [ordered]@{}
foreach ($table in $tables) {
    $count = docker exec -e "MYSQL_PWD=$rootPassword" $MySqlContainer `
        mysql -N -uroot $MySqlDatabase -e "SELECT COUNT(*) FROM $table"
    if ($LASTEXITCODE -ne 0) { throw "MySQL row-count verification failed: $table" }
    $tableCounts[$table] = [int]$count
}

Write-Host "[3/4] Copying reproducibility metadata..." -ForegroundColor Cyan
Copy-Item -LiteralPath (Join-Path $projectRoot "knowledge_corpus\index_manifest.json") -Destination $backupDir
Copy-Item -LiteralPath (Join-Path $projectRoot "knowledge_corpus\source_registry.json") -Destination $backupDir

Write-Host "[4/4] Generating backup manifest..." -ForegroundColor Cyan
$files = Get-ChildItem -LiteralPath $backupDir -File | Sort-Object Name
$entries = foreach ($file in $files) {
    [ordered]@{
        file = $file.Name
        size_bytes = [int64]$file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mysql_container = $MySqlContainer
    mysql_database = $MySqlDatabase
    es_url = $EsUrl
    es_index = $EsIndex
    es_document_count = [int]$esExport.documents
    mysql_table_counts = $tableCounts
    files = $entries
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $backupDir "BACKUP_MANIFEST.json")
Write-Host "Backup completed." -ForegroundColor Green
Write-Host "  Directory: $backupDir"
