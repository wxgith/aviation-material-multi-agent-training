param(
    [string]$OutputRoot = "",
    [string]$PackageName = "",
    [switch]$Final,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputRoot) { $OutputRoot = Join-Path $projectRoot "release_packages" }
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$OutputRoot = (Resolve-Path $OutputRoot).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$edition = if ($Final) { "final" } else { "candidate" }
if (-not $PackageName) { $PackageName = "aviation-material-agents_${edition}_$stamp" }
$packageRoot = Join-Path $OutputRoot $PackageName
if (Test-Path -LiteralPath $packageRoot) { throw "Package directory already exists: $packageRoot" }
New-Item -ItemType Directory -Path $packageRoot | Out-Null

function Copy-DirectoryFiltered {
    param([string]$Source, [string]$Destination, [string[]]$ExcludeDirectories = @(), [string[]]$ExcludeFiles = @())
    if (-not (Test-Path -LiteralPath $Source)) { throw "Required directory missing: $Source" }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $arguments = @($Source, $Destination, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
    if ($ExcludeDirectories.Count -gt 0) { $arguments += "/XD"; $arguments += $ExcludeDirectories }
    if ($ExcludeFiles.Count -gt 0) { $arguments += "/XF"; $arguments += $ExcludeFiles }
    & robocopy @arguments | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE): $Source" }
}

function Copy-RootFile {
    param([string]$RelativePath)
    $source = Join-Path $projectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) { throw "Required file missing: $RelativePath" }
    $destination = Join-Path $packageRoot $RelativePath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Remove-PackagePathSafely {
    param([string]$Path)
    $resolvedRoot = [IO.Path]::GetFullPath($packageRoot).TrimEnd("\") + "\"
    $resolvedTarget = [IO.Path]::GetFullPath($Path)
    if (-not $resolvedTarget.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside package root: $resolvedTarget"
    }
    if (Test-Path -LiteralPath $resolvedTarget) { Remove-Item -LiteralPath $resolvedTarget -Recurse -Force }
}

function Get-SubmissionDirectory {
    param([string]$Root, [string]$Number)
    $match = @(Get-ChildItem -LiteralPath $Root -Directory | Where-Object { $_.Name -like "${Number}_*" })
    if ($match.Count -ne 1) { throw "Expected one submission directory with prefix ${Number}_, found $($match.Count)." }
    return $match[0]
}

Write-Host "[1/7] Copying source code and deploy files..." -ForegroundColor Cyan
Copy-DirectoryFiltered (Join-Path $projectRoot "backend") (Join-Path $packageRoot "backend") @(".venv", ".pytest_cache", "__pycache__") @(".env", "*.pyc")
Copy-DirectoryFiltered (Join-Path $projectRoot "frontend") (Join-Path $packageRoot "frontend") @("node_modules", "__pycache__") @("*.log")
Copy-DirectoryFiltered (Join-Path $projectRoot "evaluation") (Join-Path $packageRoot "evaluation") @("__pycache__") @("*.pyc", "*.inspect.ndjson", "blind_case_key_private.json")
Copy-DirectoryFiltered (Join-Path $projectRoot "docs") (Join-Path $packageRoot "docs")
Copy-DirectoryFiltered (Join-Path $projectRoot "scripts") (Join-Path $packageRoot "scripts")
Copy-DirectoryFiltered (Join-Path $projectRoot "deploy") (Join-Path $packageRoot "deploy") @() @(".env")

Write-Host "[2/7] Copying the reproducible knowledge corpus..." -ForegroundColor Cyan
$corpusTarget = Join-Path $packageRoot "knowledge_corpus"
New-Item -ItemType Directory -Force -Path $corpusTarget | Out-Null
foreach ($directory in @("chunks", "parsed_docs", "experimental_assets", "literature_evidence", "qa_previews")) {
    Copy-DirectoryFiltered (Join-Path $projectRoot "knowledge_corpus\$directory") (Join-Path $corpusTarget $directory)
}
Get-ChildItem -LiteralPath (Join-Path $projectRoot "knowledge_corpus") -File |
    Where-Object { $_.Extension -in @(".md", ".json") } | Copy-Item -Destination $corpusTarget -Force
$rawTarget = Join-Path $corpusTarget "raw_docs"
New-Item -ItemType Directory -Force -Path $rawTarget | Out-Null
$teamSource = Join-Path $projectRoot "knowledge_corpus\raw_docs\team_tire"
Copy-DirectoryFiltered $teamSource (Join-Path $rawTarget "team_tire") @("pending_review") @("*.zip", "*.rar", "*.7z")

Write-Host "[3/7] Copying competition materials and acceptance evidence..." -ForegroundColor Cyan
$submissionSource = Join-Path $projectRoot "submission_materials"
$submissionTarget = Join-Path $packageRoot "submission_materials"
Copy-DirectoryFiltered $submissionSource $submissionTarget @("__pycache__", ".pytest_cache") @(
    "*.pyc", "*.inspect.ndjson", "blind_case_key_private.json",
    "SUBMISSION_MANIFEST.json", "SUBMISSION_MANIFEST.md",
    "请将报名表放在这里.md", "请将正式PPT放在这里.md", "请将演示视频放在这里.md"
)
foreach ($outputName in @("reviewer_verification", "deployment_validation", "demo")) {
    $source = Join-Path $projectRoot "outputs\$outputName"
    if (Test-Path -LiteralPath $source) { Copy-DirectoryFiltered $source (Join-Path $packageRoot "outputs\$outputName") }
}
$rootFiles = @(
    ".gitignore", ".dockerignore", "README.md", "API_TEST.md", "DEMO_SCRIPT.md", "DEPLOYMENT_GUIDE.md",
    "DEPLOYMENT_VALIDATION.md", "COMPETITION_DELIVERY_GUIDE.md", "EVALUATOR_QUICKSTART.md", "RELEASE_PACKAGE_README.md",
    "REMAINING_IMPROVEMENTS.md", "FINAL_FUNCTIONAL_AUDIT.md", "FINAL_RELEASE.md", "CURRENT_ACCEPTANCE_SUMMARY.md",
    "PPT_OUTLINE.md", "SCREENSHOT_GUIDE.md", "SUBMISSION_CHECKLIST.md", "SYSTEM_DESIGN.md", "competition_baseline.json"
)
foreach ($file in $rootFiles) { Copy-RootFile $file }

# Keep one unambiguous formal PPT in the review package. Historical decks stay in the working tree.
$pptMaterialTarget = (Get-SubmissionDirectory $submissionTarget "03").FullName
$formalPpts = @(Get-ChildItem -LiteralPath $pptMaterialTarget -File -Filter "*.pptx" | Where-Object { $_.Name -like "*正式提交版.pptx" })
if ($formalPpts.Count -ne 1) { throw "Expected one formal PPT, found $($formalPpts.Count)." }
$formalPpt = $formalPpts[0]
Get-ChildItem -LiteralPath $pptMaterialTarget -File -Filter "*.pptx" |
    Where-Object { $_.FullName -ne $formalPpt.FullName } |
    ForEach-Object { Remove-PackagePathSafely $_.FullName }
Get-ChildItem -LiteralPath $pptMaterialTarget -File |
    Where-Object { $_.Name -like "*.inspect.ndjson" -or $_.Name -like "*预览.png" } |
    ForEach-Object { Remove-PackagePathSafely $_.FullName }
Get-ChildItem -LiteralPath $pptMaterialTarget -Directory |
    Where-Object { $_.Name -notin @("assets", "screenshots_final") } |
    ForEach-Object { Remove-PackagePathSafely $_.FullName }

Write-Host "[4/7] Checking required competition deliverables..." -ForegroundColor Cyan
$required = @(
    "backend/app/main.py", "backend/tests/test_orchestrator.py", "frontend/package.json", "frontend/dist/index.html",
    "knowledge_corpus/index_manifest.json", "knowledge_corpus/chunks/aviation_material_chunks.json",
    "evaluation/eval_cases.json", "competition_baseline.json", "evaluation/review_gate_ablation_report.md",
    "outputs/demo/demo_preflight_latest.json"
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $packageRoot $_)) })
if ($missing.Count -gt 0) { throw "Required package files are missing: $($missing -join ', ')" }
$designDir = (Get-SubmissionDirectory $submissionTarget "01").FullName
$designFiles = @(Get-ChildItem -LiteralPath $designDir -File | Where-Object { $_.Extension -in @(".docx", ".pdf") -and $_.Name -like "*作品设计实现方案*" })
if ($designFiles.Count -eq 0) { throw "No formal design document (.docx or .pdf) found in submission section 01." }
if (-not (Test-Path -LiteralPath $formalPpt.FullName)) { throw "Formal PPT was not retained in the package." }
$section05 = (Get-SubmissionDirectory $submissionTarget "05").FullName
$section06 = (Get-SubmissionDirectory $submissionTarget "06").FullName
$section07 = (Get-SubmissionDirectory $submissionTarget "07").FullName
if (@(Get-ChildItem -LiteralPath $section05 -Recurse -File -Filter "*.md").Count -eq 0) { throw "Submission section 05 has no deployment document." }
foreach ($example in @("undergrad_basic_tire_complete_example.json", "grad_materials_brake_complete_example.json")) {
    if (@(Get-ChildItem -LiteralPath $section06 -Recurse -File -Filter $example).Count -eq 0) { throw "Required complete example missing: $example" }
}
if (@(Get-ChildItem -LiteralPath $section07 -Recurse -File -Filter "*.md").Count -eq 0) { throw "Submission section 07 has no test summary." }
$videoDir = (Get-SubmissionDirectory $submissionTarget "04").FullName
$videoFiles = @(Get-ChildItem -LiteralPath $videoDir -File -Filter "*.mp4" -ErrorAction SilentlyContinue)
$registrationFiles = @(Get-ChildItem -LiteralPath $submissionTarget -File | Where-Object { $_.Name -like "*报名表*" -and $_.Extension -in @(".doc", ".docx", ".xls", ".xlsx", ".pdf") })
if ($Final -and $videoFiles.Count -eq 0) { throw "Final package requires an MP4 demonstration video." }
if ($Final -and $registrationFiles.Count -eq 0) { throw "Final package requires the completed registration form." }

Write-Host "[5/7] Running secret and forbidden-path checks..." -ForegroundColor Cyan
foreach ($relative in @("backend\.env", "backend\.venv", "frontend\node_modules", ".tmp", "logs", "knowledge_corpus\raw_docs\team_tire\pending_review")) {
    if (Test-Path -LiteralPath (Join-Path $packageRoot $relative)) { throw "Forbidden path entered package: $relative" }
}
$unexpectedEnvFiles = @(Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object { $_.Name -eq ".env" })
if ($unexpectedEnvFiles.Count -gt 0) { throw "Uncommitted .env file entered package: $($unexpectedEnvFiles[0].FullName)" }
$textExtensions = @(".env", ".example", ".md", ".txt", ".json", ".py", ".js", ".jsx", ".ps1", ".yml", ".yaml")
$secretHits = @(Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object { $textExtensions -contains $_.Extension } | Select-String -Pattern "(?<![A-Za-z0-9])sk-[A-Za-z0-9._-]{24,}" -ErrorAction SilentlyContinue)
if ($secretHits.Count -gt 0) { throw "Potential API key detected in package: $($secretHits[0].Path)" }

Write-Host "[6/7] Generating package manifest..." -ForegroundColor Cyan
$manifestJson = Join-Path $packageRoot "PACKAGE_MANIFEST.json"
$manifestMd = Join-Path $packageRoot "PACKAGE_MANIFEST.md"
$manifestFiles = Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object { $_.FullName -notin @($manifestJson, $manifestMd) } | Sort-Object FullName
$entries = foreach ($file in $manifestFiles) {
    [ordered]@{
        path = $file.FullName.Substring($packageRoot.Length).TrimStart("\").Replace("\", "/")
        size_bytes = [int64]$file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
$manifest = [ordered]@{
    package_name = $PackageName; edition = $edition; generated_at = (Get-Date).ToUniversalTime().ToString("o")
    algorithm = "SHA-256"; file_count = @($entries).Count
    total_size_bytes = [int64](($manifestFiles | Measure-Object Length -Sum).Sum)
    video_included = $videoFiles.Count -gt 0; registration_form_included = $registrationFiles.Count -gt 0
    source_secrets_included = $false; files = $entries
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $manifestJson
@(
    "# Package manifest", "", "- Package: ``$PackageName``", "- Edition: $edition",
    "- Files: $($manifest.file_count)", "- Total size: $([math]::Round($manifest.total_size_bytes / 1MB, 2)) MB",
    "- Demo video included: $($manifest.video_included)", "- Registration form included: $($manifest.registration_form_included)",
    "- Secrets included: false", "", "Per-file SHA-256 hashes are recorded in ``PACKAGE_MANIFEST.json``."
) -join "`n" | Set-Content -Encoding UTF8 $manifestMd

if ($SkipZip) {
    Write-Host "[7/7] ZIP skipped." -ForegroundColor Yellow
    Write-Host "Package directory: $packageRoot" -ForegroundColor Green
    exit 0
}
Write-Host "[7/7] Creating ZIP and SHA-256..." -ForegroundColor Cyan
$zipPath = "$packageRoot.zip"
# Python's zipfile preserves UTF-8 paths and stores already-compressed assets
# without wasting time recompressing MP4/PPTX/DOCX content.
& python (Join-Path $PSScriptRoot "create_release_zip.py") $packageRoot $zipPath
if ($LASTEXITCODE -ne 0) { throw "create_release_zip.py failed (exit $LASTEXITCODE)." }
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$zipHash  $([IO.Path]::GetFileName($zipPath))" | Set-Content -Encoding UTF8 "$zipPath.sha256.txt"
Write-Host "Release package created." -ForegroundColor Green
Write-Host "  Directory: $packageRoot"
Write-Host "  ZIP:       $zipPath"
Write-Host "  SHA-256:   $zipHash"
Write-Host "  Final:     $Final"
