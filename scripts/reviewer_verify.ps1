param(
    [ValidateSet("mock", "engineering", "all")]
    [string]$Mode = "mock",
    [string]$ApiBase = "http://127.0.0.1:8000/api",
    [string]$EsUrl = "",
    [switch]$RunRegression
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$outputDir = Join-Path $projectRoot "outputs\reviewer_verification"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Create backend/.venv or install Python 3.11+."
    }
    $python = $pythonCommand.Source
}

$checks = [System.Collections.Generic.List[object]]::new()

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $script:checks.Add([ordered]@{
        name = $Name
        passed = $Passed
        detail = $Detail
    })
    $color = if ($Passed) { "Green" } else { "Red" }
    $label = if ($Passed) { "PASS" } else { "FAIL" }
    Write-Host "[$label] $Name - $Detail" -ForegroundColor $color
    if (-not $Passed) { throw "$Name failed: $Detail" }
}

function Invoke-MockVerification {
    Write-Host "`n[Mock verification] No SQL, Elasticsearch, BGE or LLM key is used." -ForegroundColor Cyan
    Push-Location $backendDir
    try {
        $output = & $python -m app.evaluation.fallback_acceptance --quiet
        if ($LASTEXITCODE -ne 0) { throw "Fallback acceptance exited with code $LASTEXITCODE." }
    }
    finally {
        Pop-Location
    }

    $resultPath = Join-Path $projectRoot "evaluation\fallback_acceptance_results.json"
    if (-not (Test-Path -LiteralPath $resultPath)) { throw "Fallback result was not generated." }
    $result = Get-Content -Raw -Encoding UTF8 $resultPath | ConvertFrom-Json
    Add-Check "Mock closed loop" ($result.status -eq "passed") "status=$($result.status)"
    Add-Check "Six Agent pipeline" ($result.flow.agent_step_count -eq 6) "steps=$($result.flow.agent_step_count)"
    Add-Check "Four resource forms" ($result.flow.resource_forms.Count -eq 4) "resources=$($result.flow.resource_forms.Count)"
    Add-Check "Feedback iteration" ($result.flow.feedback_iteration_steps -eq 4) "steps=$($result.flow.feedback_iteration_steps)"
    Add-Check "No external knowledge service" ($result.mode.knowledge_source -eq "local-json") "source=$($result.mode.knowledge_source)"
}

function Invoke-EngineeringVerification {
    Write-Host "`n[Engineering verification] The running API is inspected; no LLM key is required." -ForegroundColor Cyan
    $health = Invoke-RestMethod "$ApiBase/health" -TimeoutSec 10
    Add-Check "Backend API" ($health.backend_status -eq "ok") "version=$($health.version)"
    Add-Check "MySQL connection" ([bool]$health.database_connected) "data_backend=$($health.data_backend)"
    Add-Check "Elasticsearch connection" ([bool]$health.es_connected) "source=$($health.knowledge_source)"
    Add-Check "Elasticsearch selected" ($health.knowledge_source -eq "elasticsearch") "index=$($health.es_index)"
    Add-Check "LLM fallback available" ([bool]$health.llm.fallback_enabled) "mode=$($health.llm.mode)"

    $profiles = Invoke-RestMethod "$ApiBase/profiles" -TimeoutSec 10
    $domains = Invoke-RestMethod "$ApiBase/domains" -TimeoutSec 10
    $questions = Invoke-RestMethod "$ApiBase/questions?domain=tire" -TimeoutSec 10
    Add-Check "Learner profiles" ($profiles.Count -ge 3) "count=$($profiles.Count)"
    Add-Check "Training domains" ($domains.Count -ge 3) "count=$($domains.Count)"
    Add-Check "Diagnostic questions" ($questions.Count -ge 5) "count=$($questions.Count)"

    $effectiveEsUrl = if ($EsUrl) { $EsUrl } else { $health.es_url }
    $esCount = Invoke-RestMethod "$($effectiveEsUrl.TrimEnd('/'))/$($health.es_index)/_count" -TimeoutSec 10
    Add-Check "Elasticsearch corpus" ([int]$esCount.count -gt 0) "documents=$($esCount.count)"
}

function Invoke-RegressionVerification {
    Write-Host "`n[Regression verification] Running backend tests and frontend production build." -ForegroundColor Cyan
    Push-Location $backendDir
    try {
        & $python -m pytest -q
        Add-Check "Backend regression" ($LASTEXITCODE -eq 0) "pytest completed"
    }
    finally {
        Pop-Location
    }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) { throw "npm was not found. Install Node.js 20+." }
    Push-Location $frontendDir
    try {
        & $npm.Source run build
        Add-Check "Frontend production build" ($LASTEXITCODE -eq 0) "vite build completed"
    }
    finally {
        Pop-Location
    }
}

if ($Mode -in @("mock", "all")) { Invoke-MockVerification }
if ($Mode -in @("engineering", "all")) { Invoke-EngineeringVerification }
if ($RunRegression) { Invoke-RegressionVerification }

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$report = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = $Mode
    api_base = $ApiBase
    es_url_override = $EsUrl
    llm_key_required = $false
    regression_included = [bool]$RunRegression
    status = "passed"
    checks = $checks
}
$jsonPath = Join-Path $outputDir "reviewer_verification_latest.json"
$markdownPath = Join-Path $outputDir "reviewer_verification_latest.md"
$report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $jsonPath

$rows = @(
    "# Reviewer verification report",
    "",
    "- Generated: ``$($report.generated_at)``",
    "- Mode: ``$Mode``",
    "- LLM API key required: **No**",
    "- Result: **PASS**",
    "",
    "| Check | Result | Detail |",
    "| --- | --- | --- |"
)
foreach ($check in $checks) {
    $rows += "| $($check.name) | PASS | $($check.detail) |"
}
$rows -join "`n" | Set-Content -Encoding UTF8 $markdownPath

Write-Host "`nReviewer verification passed without an LLM API key." -ForegroundColor Green
Write-Host "  JSON: $jsonPath"
Write-Host "  Markdown: $markdownPath"
