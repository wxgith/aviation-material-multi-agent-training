$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$submissionDir = Join-Path $projectRoot "submission_materials\07_接口测试与单元测试"

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found: $python"
}

Push-Location $backendDir
try {
    & $python -m app.evaluation.fallback_acceptance --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "JSON/mock fallback acceptance failed."
    }
}
finally {
    Pop-Location
}

New-Item -ItemType Directory -Force -Path $submissionDir | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\fallback_acceptance_results.json") `
    -Destination (Join-Path $submissionDir "JSON兜底模式验收报告.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\fallback_acceptance_summary.md") `
    -Destination (Join-Path $submissionDir "JSON兜底模式验收报告.md") -Force

Write-Host "JSON/mock fallback acceptance passed." -ForegroundColor Green
Write-Host "  Report: $submissionDir\JSON兜底模式验收报告.md"
