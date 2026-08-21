param(
    [string]$MaterialRoot = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $MaterialRoot) {
    $MaterialRoot = Join-Path $projectRoot "submission_materials"
}
$MaterialRoot = (Resolve-Path $MaterialRoot).Path
$jsonPath = Join-Path $MaterialRoot "SUBMISSION_MANIFEST.json"
$markdownPath = Join-Path $MaterialRoot "SUBMISSION_MANIFEST.md"

$excluded = @("SUBMISSION_MANIFEST.json", "SUBMISSION_MANIFEST.md")
$files = Get-ChildItem -LiteralPath $MaterialRoot -Recurse -File |
    Where-Object { $excluded -notcontains $_.Name } |
    Sort-Object FullName

$entries = foreach ($file in $files) {
    $relative = $file.FullName.Substring($MaterialRoot.Length).TrimStart("\").Replace("\", "/")
    [ordered]@{
        path = $relative
        size_bytes = [int64]$file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$required = @(
    "01_作品设计实现方案/SYSTEM_DESIGN.md",
    "02_作品简介与创新点/作品简介.md",
    "02_作品简介与创新点/创新点与应用价值.md",
    "03_答辩PPT材料/航空工程材料多智能体训练系统_答辩PPT_正式提交版.pptx",
    "04_演示视频材料/DEMO_SCRIPT.md",
    "05_系统运行与部署说明/README.md",
    "06_测试数据与知识库/knowledge_corpus/index_manifest.json",
    "07_接口测试与单元测试/competition_baseline.json",
    "07_接口测试与单元测试/当前验收摘要.md",
    "07_接口测试与单元测试/JSON兜底模式验收报告.json",
    "03_答辩PPT材料/screenshots_final/17_上下文助手_诊断反馈与下一动作.png"
)
$entryPaths = @($entries | ForEach-Object { $_.path })
$requiredStatus = foreach ($path in $required) {
    [ordered]@{ path = $path; present = $entryPaths -contains $path }
}
$missing = @($requiredStatus | Where-Object { -not $_.present })

$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    root = "submission_materials"
    algorithm = "SHA-256"
    file_count = @($entries).Count
    total_size_bytes = [int64](($files | Measure-Object Length -Sum).Sum)
    required_files = $requiredStatus
    required_status = if ($missing.Count -eq 0) { "complete" } else { "missing_files" }
    files = $entries
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 $jsonPath

$lines = @(
    "# 提交包完整性清单",
    "",
    "生成时间：``$($manifest.generated_at)``",
    "",
    "- 哈希算法：SHA-256",
    "- 文件数量：$($manifest.file_count)",
    "- 总大小：$([math]::Round($manifest.total_size_bytes / 1MB, 2)) MB",
    "- 必需文件状态：$($manifest.required_status)",
    "",
    "## 必需文件",
    "",
    "| 路径 | 状态 |",
    "| --- | --- |"
)
foreach ($item in $requiredStatus) {
    $lines += "| ``$($item.path)`` | $(if ($item.present) { '存在' } else { '缺失' }) |"
}
$lines += @(
    "",
    "完整逐文件 SHA-256 记录见 ``SUBMISSION_MANIFEST.json``。正式加入报名表、PPT 修订版或演示视频后，应重新运行生成命令。"
)
$lines -join "`n" | Set-Content -Encoding utf8 $markdownPath

if ($missing.Count -gt 0) {
    Write-Error "Submission manifest generated, but required files are missing: $($missing.path -join ', ')"
}

Write-Host "Submission manifest generated." -ForegroundColor Green
Write-Host "  Files: $($manifest.file_count)"
Write-Host "  Size:  $([math]::Round($manifest.total_size_bytes / 1MB, 2)) MB"
Write-Host "  JSON:  $jsonPath"
Write-Host "  MD:    $markdownPath"
