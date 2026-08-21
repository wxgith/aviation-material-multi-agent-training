param(
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [string]$MySqlContainer = "report-mysql",
    [string]$MySqlDatabase = "agents",
    [string]$EsUrl = "http://127.0.0.1:9201",
    [string]$EsIndex = "aviation_material_knowledge",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
if (-not $Force) { throw "Restore overwrites SQL tables and the ES index. Re-run with -Force after verifying the backup." }
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$resolved = (Resolve-Path -LiteralPath $BackupDir).Path
$manifestPath = Join-Path $resolved "BACKUP_MANIFEST.json"
$sqlPath = Join-Path $resolved "mysql-$MySqlDatabase.sql"
$esPath = Join-Path $resolved "elasticsearch-$EsIndex.ndjson"
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "BACKUP_MANIFEST.json was not found." }
if (-not (Test-Path -LiteralPath $sqlPath)) { throw "MySQL dump was not found: $sqlPath" }
if (-not (Test-Path -LiteralPath $esPath)) { throw "ES archive was not found: $esPath" }

$manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $file = Join-Path $resolved $entry.file
    if (-not (Test-Path -LiteralPath $file)) { throw "Backup file is missing: $($entry.file)" }
    $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $entry.sha256) { throw "Backup checksum mismatch: $($entry.file)" }
}

$running = docker ps --filter "name=^/$MySqlContainer$" --format "{{.Names}}"
if ($running -ne $MySqlContainer) { throw "MySQL container is not running: $MySqlContainer" }
$containerPath = "/tmp/agents-restore.sql"
$containerEnv = docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $MySqlContainer
$rootLine = $containerEnv | Where-Object { $_ -like "MYSQL_ROOT_PASSWORD=*" } | Select-Object -First 1
if (-not $rootLine) { throw "MYSQL_ROOT_PASSWORD was not found in container configuration." }
$rootPassword = $rootLine.Substring("MYSQL_ROOT_PASSWORD=".Length)

Write-Host "[1/3] Restoring MySQL..." -ForegroundColor Cyan
docker cp $sqlPath "${MySqlContainer}:$containerPath" | Out-Null
docker exec -e "MYSQL_PWD=$rootPassword" $MySqlContainer sh -c `
    "mysql -uroot $MySqlDatabase < $containerPath"
if ($LASTEXITCODE -ne 0) { throw "MySQL restore failed." }
docker exec $MySqlContainer rm -f $containerPath | Out-Null

Write-Host "[2/3] Restoring Elasticsearch..." -ForegroundColor Cyan
Push-Location (Join-Path $projectRoot "backend")
try {
    & $python -m app.ops.es_archive restore --url $EsUrl --index $EsIndex --file $esPath --replace
    if ($LASTEXITCODE -ne 0) { throw "Elasticsearch restore failed." }
}
finally { Pop-Location }

Write-Host "[3/3] Verifying counts..." -ForegroundColor Cyan
$esCount = Invoke-RestMethod "$($EsUrl.TrimEnd('/'))/$EsIndex/_count" -TimeoutSec 15
Write-Host "Restore completed." -ForegroundColor Green
Write-Host "  Elasticsearch documents: $($esCount.count)"
Write-Host "  Restart the backend before using restored data."
