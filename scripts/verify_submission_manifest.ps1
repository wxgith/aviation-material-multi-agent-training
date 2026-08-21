param(
    [string]$MaterialRoot = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $MaterialRoot) {
    $MaterialRoot = Join-Path $projectRoot "submission_materials"
}
$MaterialRoot = (Resolve-Path $MaterialRoot).Path
$manifestPath = Join-Path $MaterialRoot "SUBMISSION_MANIFEST.json"
if (-not (Test-Path $manifestPath)) {
    throw "Manifest not found: $manifestPath"
}

$manifest = Get-Content -Raw -Encoding utf8 $manifestPath | ConvertFrom-Json
$issues = @()
foreach ($entry in $manifest.files) {
    $fullPath = Join-Path $MaterialRoot ($entry.path.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $fullPath)) {
        $issues += "MISSING: $($entry.path)"
        continue
    }
    $file = Get-Item -LiteralPath $fullPath
    if ([int64]$file.Length -ne [int64]$entry.size_bytes) {
        $issues += "SIZE: $($entry.path)"
        continue
    }
    $hash = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $entry.sha256) {
        $issues += "HASH: $($entry.path)"
    }
}

$tracked = @($manifest.files | ForEach-Object { $_.path })
$extra = Get-ChildItem -LiteralPath $MaterialRoot -Recurse -File |
    Where-Object { $_.Name -notin @("SUBMISSION_MANIFEST.json", "SUBMISSION_MANIFEST.md") } |
    ForEach-Object { $_.FullName.Substring($MaterialRoot.Length).TrimStart("\").Replace("\", "/") } |
    Where-Object { $tracked -notcontains $_ }
foreach ($path in $extra) { $issues += "UNTRACKED: $path" }

if ($issues.Count -gt 0) {
    $issues | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    throw "Submission manifest verification failed with $($issues.Count) issue(s)."
}

Write-Host "Submission manifest verification passed." -ForegroundColor Green
Write-Host "  Files verified: $($manifest.file_count)"
Write-Host "  Algorithm:      $($manifest.algorithm)"
