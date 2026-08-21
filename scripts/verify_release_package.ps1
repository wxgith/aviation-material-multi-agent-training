param([Parameter(Mandatory = $true)][string]$PackagePath)

$ErrorActionPreference = "Stop"
$resolved = (Resolve-Path -LiteralPath $PackagePath).Path
$packageRoot = $resolved
$temporaryRoot = $null
if ([IO.Path]::GetExtension($resolved) -eq ".zip") {
    $temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("aviation-package-check-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    Expand-Archive -LiteralPath $resolved -DestinationPath $temporaryRoot
    $roots = @(Get-ChildItem -LiteralPath $temporaryRoot -Directory)
    if ($roots.Count -ne 1) { throw "ZIP must contain exactly one top-level directory." }
    $packageRoot = $roots[0].FullName
}
try {
    $manifestPath = Join-Path $packageRoot "PACKAGE_MANIFEST.json"
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw "PACKAGE_MANIFEST.json not found." }
    $manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
    $issues = @()
    foreach ($entry in $manifest.files) {
        $fullPath = Join-Path $packageRoot ($entry.path.Replace("/", "\"))
        if (-not (Test-Path -LiteralPath $fullPath)) { $issues += "MISSING: $($entry.path)"; continue }
        $file = Get-Item -LiteralPath $fullPath
        if ([int64]$file.Length -ne [int64]$entry.size_bytes) { $issues += "SIZE: $($entry.path)"; continue }
        $hash = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $entry.sha256) { $issues += "HASH: $($entry.path)" }
    }
    $manifestPaths = @($manifest.files | ForEach-Object { $_.path })
    $actualPaths = @(Get-ChildItem -LiteralPath $packageRoot -Recurse -File | ForEach-Object {
        $_.FullName.Substring($packageRoot.Length).TrimStart("\").Replace("\", "/")
    } | Where-Object { $_ -notin @("PACKAGE_MANIFEST.json", "PACKAGE_MANIFEST.md") })
    foreach ($actualPath in $actualPaths) {
        if ($manifestPaths -notcontains $actualPath) { $issues += "UNMANIFESTED: $actualPath" }
    }
    foreach ($relative in @("backend\.env", "backend\.venv", "frontend\node_modules", "logs")) { if (Test-Path -LiteralPath (Join-Path $packageRoot $relative)) { $issues += "FORBIDDEN: $relative" } }
    Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object { $_.Name -eq ".env" } | ForEach-Object { $issues += "FORBIDDEN ENV: $($_.FullName)" }
    $textExtensions = @(".env", ".example", ".md", ".txt", ".json", ".py", ".js", ".jsx", ".ps1", ".yml", ".yaml")
    $secretHits = @(Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object { $textExtensions -contains $_.Extension } | Select-String -Pattern "(?<![A-Za-z0-9])sk-[A-Za-z0-9._-]{24,}" -ErrorAction SilentlyContinue)
    if ($secretHits.Count -gt 0) { $issues += "POTENTIAL API KEY: $($secretHits[0].Path)" }
    if ($issues.Count -gt 0) { $issues | ForEach-Object { Write-Host $_ -ForegroundColor Red }; throw "Release package verification failed with $($issues.Count) issue(s)." }
    Write-Host "Release package verification passed." -ForegroundColor Green
    Write-Host "  Package: $($manifest.package_name)"
    Write-Host "  Edition: $($manifest.edition)"
    Write-Host "  Files:   $($manifest.file_count)"
    Write-Host "  Video:   $($manifest.video_included)"
    Write-Host "  Form:    $($manifest.registration_form_included)"
}
finally {
    if ($temporaryRoot -and (Test-Path -LiteralPath $temporaryRoot)) { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force }
}

