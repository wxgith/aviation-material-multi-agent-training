param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$EsUrl = "http://127.0.0.1:9201",
    [string]$EsIndex = "aviation_material_knowledge",
    [ValidateSet(0, 3)]
    [int]$OnlyStep = 0,
    [int]$CommandTimeoutSeconds = 900,
    [int]$Step3TimeoutSeconds = 120,
    [int]$HeartbeatSeconds = 15
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$outputDir = Join-Path $projectRoot "outputs\acceptance"
$submissionDir = Join-Path $projectRoot "submission_materials\07_接口测试与单元测试"
$jsonPath = Join-Path $outputDir "acceptance_latest.json"
$markdownPath = Join-Path $outputDir "acceptance_latest.md"
$logDir = Join-Path $outputDir "logs"

function ConvertTo-BatchArgument {
    param([string]$Value)
    return '"' + (($Value -replace '%', '%%') -replace '"', '""') + '"'
}

function Invoke-StreamingCommand {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutSeconds
    )
    $safeLabel = $Label -replace "[^A-Za-z0-9_-]", "-"
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $stdoutPath = Join-Path $logDir "$stamp-$safeLabel.stdout.log"
    $stderrPath = Join-Path $logDir "$stamp-$safeLabel.stderr.log"
    $exitCodePath = Join-Path $logDir "$stamp-$safeLabel.exitcode.log"
    $runnerPath = Join-Path $logDir "$stamp-$safeLabel.runner.cmd"
    $startedAt = Get-Date
    $lastHeartbeat = $startedAt
    $lastProgressStart = "not reported"
    $stdoutCount = 0
    $stderrCount = 0
    $allOutput = @()
    $previousPythonIoEncoding = $env:PYTHONIOENCODING
    $previousPythonUtf8 = $env:PYTHONUTF8

    Write-Host "  command: $FilePath $($Arguments -join ' ')" -ForegroundColor DarkGray
    Write-Host "  timeout: ${TimeoutSeconds}s; logs: $stdoutPath" -ForegroundColor DarkGray
    if ((Split-Path -Leaf $FilePath) -match "^python(?:\.exe)?$") {
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
    }
    $commandParts = @((ConvertTo-BatchArgument $FilePath))
    $commandParts += @($Arguments | ForEach-Object { ConvertTo-BatchArgument $_ })
    $batchLines = @(
        "@echo off",
        "cd /d $(ConvertTo-BatchArgument $WorkingDirectory)",
        ($commandParts -join " "),
        'set "_acceptance_exit_code=!ERRORLEVEL!"',
        "echo !_acceptance_exit_code!>$(ConvertTo-BatchArgument $exitCodePath)",
        'exit /b !_acceptance_exit_code!'
    )
    $batchLines | Set-Content -LiteralPath $runnerPath -Encoding ASCII
    try {
        $process = Start-Process -FilePath $env:ComSpec -ArgumentList @("/d", "/e:on", "/v:on", "/c", "`"$runnerPath`"") `
            -WorkingDirectory $WorkingDirectory -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    }
    finally {
        $env:PYTHONIOENCODING = $previousPythonIoEncoding
        $env:PYTHONUTF8 = $previousPythonUtf8
    }

    while (-not $process.HasExited) {
        Start-Sleep -Milliseconds 250
        $stdout = @(Get-Content -LiteralPath $stdoutPath -Encoding UTF8 -ErrorAction SilentlyContinue)
        $stderr = @(Get-Content -LiteralPath $stderrPath -Encoding UTF8 -ErrorAction SilentlyContinue)
        if ($stdout.Count -gt $stdoutCount) {
            $newLines = @($stdout[$stdoutCount..($stdout.Count - 1)])
            $newLines | ForEach-Object {
                Write-Host $_
                if ($_ -match '^\[START\]') { $lastProgressStart = $_ }
            }
            $allOutput += $newLines
            $stdoutCount = $stdout.Count
            $lastHeartbeat = Get-Date
        }
        if ($stderr.Count -gt $stderrCount) {
            $newLines = @($stderr[$stderrCount..($stderr.Count - 1)])
            $newLines | ForEach-Object { Write-Host $_ -ForegroundColor DarkYellow }
            $allOutput += $newLines
            $stderrCount = $stderr.Count
            $lastHeartbeat = Get-Date
        }
        if ($process.HasExited) {
            break
        }
        $elapsed = ((Get-Date) - $startedAt).TotalSeconds
        if ($elapsed -ge $TimeoutSeconds) {
            if (-not $process.HasExited) {
                try {
                    & taskkill.exe /PID $process.Id /T /F *> $null
                }
                catch {
                    # The child can exit between the status check and taskkill.
                }
            }
            Remove-Item -LiteralPath $runnerPath -Force -ErrorAction SilentlyContinue
            Write-Host "  TIMEOUT: $Label exceeded ${TimeoutSeconds}s (PID $($process.Id))." -ForegroundColor Red
            Write-Host "  Last progress: $lastProgressStart" -ForegroundColor Yellow
            Write-Host "  Logs: $stdoutPath, $stderrPath" -ForegroundColor Yellow
            throw "$Label timed out after ${TimeoutSeconds}s. Last progress: $lastProgressStart"
        }
        if (((Get-Date) - $lastHeartbeat).TotalSeconds -ge $HeartbeatSeconds) {
            Write-Host "  ... $Label still running; elapsed $([int]$elapsed)s, PID $($process.Id)" -ForegroundColor DarkGray
            $lastHeartbeat = Get-Date
        }
    }
    $stdout = @(Get-Content -LiteralPath $stdoutPath -Encoding UTF8 -ErrorAction SilentlyContinue)
    $stderr = @(Get-Content -LiteralPath $stderrPath -Encoding UTF8 -ErrorAction SilentlyContinue)
    if ($stdout.Count -gt $stdoutCount) {
        $newLines = @($stdout[$stdoutCount..($stdout.Count - 1)])
        $newLines | ForEach-Object {
            Write-Host $_
            if ($_ -match '^\[START\]') { $lastProgressStart = $_ }
        }
        $allOutput += $newLines
    }
    if ($stderr.Count -gt $stderrCount) {
        $newLines = @($stderr[$stderrCount..($stderr.Count - 1)])
        $newLines | ForEach-Object { Write-Host $_ -ForegroundColor DarkYellow }
        $allOutput += $newLines
    }
    $exitCodeWaitStarted = Get-Date
    while (-not (Test-Path -LiteralPath $exitCodePath)) {
        if (((Get-Date) - $exitCodeWaitStarted).TotalSeconds -ge 3) { break }
        Start-Sleep -Milliseconds 50
    }
    if (-not (Test-Path -LiteralPath $exitCodePath)) {
        Remove-Item -LiteralPath $runnerPath -Force -ErrorAction SilentlyContinue
        throw "$Label ended without an exit-code marker. Logs: $stdoutPath, $stderrPath"
    }
    $exitCodeText = (Get-Content -LiteralPath $exitCodePath -Raw -ErrorAction SilentlyContinue) -replace '\s', ''
    if ($exitCodeText -notmatch '^-?\d+$') {
        Remove-Item -LiteralPath $runnerPath -Force -ErrorAction SilentlyContinue
        throw "$Label produced an invalid exit-code marker '$exitCodeText'. Logs: $stdoutPath, $stderrPath"
    }
    $exitCode = [int]$exitCodeText
    Remove-Item -LiteralPath $runnerPath -Force -ErrorAction SilentlyContinue
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode. Last progress: $lastProgressStart. Logs: $stdoutPath, $stderrPath"
    }
    return ($allOutput -join "`n")
}

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found: $python"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $submissionDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if ($OnlyStep -eq 3) {
    Write-Host "[3/14 only] Running deterministic evaluation with live case progress..." -ForegroundColor Cyan
    Invoke-StreamingCommand "core-evaluation" $python `
        @("-u", "-m", "app.evaluation.runner", "--quiet", "--progress") `
        $backendDir $Step3TimeoutSeconds | Out-Null
    Write-Host "Step 3 completed without running the other 13 acceptance steps." -ForegroundColor Green
    exit 0
}

Write-Host "[1/14] Checking API, MySQL and Elasticsearch..." -ForegroundColor Cyan
$health = Invoke-RestMethod "$BackendUrl/api/health" -TimeoutSec 8
if (-not $health.database_connected) { throw "MySQL is not connected." }
if (-not $health.es_connected) { throw "Elasticsearch is not connected." }
Write-Host "SQL + ES ready." -ForegroundColor Green

Write-Host "[2/14] Checking Elasticsearch index..." -ForegroundColor Cyan
$esCount = Invoke-RestMethod "$EsUrl/$EsIndex/_count" -TimeoutSec 8
if ([int]$esCount.count -lt 1) { throw "Elasticsearch index is empty." }
Write-Host "ES documents: $($esCount.count)" -ForegroundColor Green

Push-Location $backendDir
try {
    Write-Host "[3/14] Running deterministic 50-case evaluation..." -ForegroundColor Cyan
    Invoke-StreamingCommand "core-evaluation" $python `
        @("-u", "-m", "app.evaluation.runner", "--quiet", "--progress") `
        $backendDir $Step3TimeoutSeconds | Out-Null

    Write-Host "[4/14] Executing all 50 cases through the 6-Agent pipeline..." -ForegroundColor Cyan
    Invoke-StreamingCommand "full-50-case-execution" $python `
        @("-u", "-m", "app.evaluation.full_case_runner", "--use-es") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[5/14] Running ReviewAgent rejection and regeneration demo..." -ForegroundColor Cyan
    Invoke-StreamingCommand "review-correction-demo" $python `
        @("-u", "-m", "app.evaluation.correction_demo_runner", "--use-es") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[6/14] Recording the confirmed expert review result..." -ForegroundColor Cyan
    Invoke-StreamingCommand "expert-review-confirmation" $python `
        @("-u", "-m", "app.evaluation.expert_confirmation_runner") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[7/14] Running 20-case experimental evidence evaluation..." -ForegroundColor Cyan
    Invoke-StreamingCommand "batch-2-evaluation" $python `
        @("-u", "-m", "app.evaluation.batch2_runner", "--quiet") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[8/14] Running 10-case literature evidence regression..." -ForegroundColor Cyan
    Invoke-StreamingCommand "literature-evidence-evaluation" $python `
        @("-u", "-m", "app.evaluation.literature_evidence_runner") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[9/14] Running 6-case FAA maintenance evidence regression..." -ForegroundColor Cyan
    Invoke-StreamingCommand "faa-maintenance-evaluation" $python `
        @("-u", "-m", "app.evaluation.maintenance_evidence_runner") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[10/14] Running 15-case guided inquiry evaluation..." -ForegroundColor Cyan
    Invoke-StreamingCommand "guided-inquiry-evaluation" $python `
        @("-u", "-m", "app.evaluation.guided_inquiry_runner", "--use-es") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[11/14] Running 39-case interface assistant evaluation (JSON + ES)..." -ForegroundColor Cyan
    Invoke-StreamingCommand "interface-assistant-json" $python `
        @("-u", "-m", "app.evaluation.interface_assistant_runner") `
        $backendDir $CommandTimeoutSeconds | Out-Null
    Invoke-StreamingCommand "interface-assistant-es" $python `
        @("-u", "-m", "app.evaluation.interface_assistant_runner", "--use-es") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[12/14] Running complete JSON/mock fallback flow..." -ForegroundColor Cyan
    Invoke-StreamingCommand "json-mock-fallback" $python `
        @("-u", "-m", "app.evaluation.fallback_acceptance", "--quiet") `
        $backendDir $CommandTimeoutSeconds | Out-Null

    Write-Host "[13/14] Running backend tests..." -ForegroundColor Cyan
    $pytestOutput = Invoke-StreamingCommand "backend-tests" $python `
        @("-u", "-m", "pytest", "-q") $backendDir $CommandTimeoutSeconds
}
finally {
    Pop-Location
}

$testCount = 0
if ($pytestOutput -match "(?m)(\d+) passed") {
    $testCount = [int]$Matches[1]
}
if ($testCount -lt 1) { throw "Could not determine pytest pass count." }

Write-Host "[14/14] Building frontend..." -ForegroundColor Cyan
Push-Location $frontendDir
$previousNoColor = $env:NO_COLOR
$previousForceColor = $env:FORCE_COLOR
try {
    $env:NO_COLOR = "1"
    $env:FORCE_COLOR = "0"
    $buildOutput = Invoke-StreamingCommand "frontend-build" "npm.cmd" `
        @("run", "build") $frontendDir $CommandTimeoutSeconds
    Write-Host "Frontend production build passed." -ForegroundColor Green
}
finally {
    $env:NO_COLOR = $previousNoColor
    $env:FORCE_COLOR = $previousForceColor
    Pop-Location
}

$core = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\automated_results.json") | ConvertFrom-Json
$fullCases = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\full_case_execution_results.json") | ConvertFrom-Json
$correction = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\review_correction_demo.json") | ConvertFrom-Json
$expert = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\expert_review_confirmation.json") | ConvertFrom-Json
$batch2 = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\batch2_automated_results.json") | ConvertFrom-Json
$literature = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\literature_evidence_results.json") | ConvertFrom-Json
$maintenance = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\maintenance_evidence_results.json") | ConvertFrom-Json
$guided = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\guided_inquiry_results.json") | ConvertFrom-Json
$assistant = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\interface_assistant_eval_results.json") | ConvertFrom-Json
$assistantEs = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\interface_assistant_eval_results_es.json") | ConvertFrom-Json
$fallback = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot "evaluation\fallback_acceptance_results.json") | ConvertFrom-Json

if ($core.overall_automated_status -ne "passed") { throw "Core evaluation did not pass." }
if ([int]$fullCases.metrics.passed_cases -ne 50) { throw "Full 50-case execution did not pass." }
if ($correction.status -ne "passed") { throw "Review correction demo did not pass." }
if ($expert.expert_review_status -ne "confirmed_accurate") { throw "Expert review confirmation is not complete." }
if ($batch2.automated_status -ne "passed") { throw "Batch-2 evaluation did not pass." }
if ($literature.automated_status -ne "passed") { throw "Literature evidence evaluation did not pass." }
if ($maintenance.automated_status -ne "passed") { throw "FAA maintenance evidence evaluation did not pass." }
if ($guided.automated_status -ne "passed") { throw "Guided inquiry evaluation did not pass." }
if ($assistant.status -ne "passed") { throw "Interface assistant evaluation did not pass." }
if ($assistantEs.status -ne "passed") { throw "Interface assistant ES evaluation did not pass." }
if ($fallback.status -ne "passed") { throw "JSON/mock fallback flow did not pass." }

$report = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    status = "passed"
    version = $health.version
    mode = [ordered]@{
        data_backend = $health.data_backend
        database_connected = [bool]$health.database_connected
        es_connected = [bool]$health.es_connected
        knowledge_source = $health.knowledge_source
        retrieval_mode = $health.retrieval_mode
        llm_enabled = [bool]$health.llm_enabled
    }
    engineering = [ordered]@{
        es_index = $EsIndex
        es_document_count = [int]$esCount.count
        backend_tests_passed = $testCount
        frontend_build = "passed"
    }
    evaluation = [ordered]@{
        core_50_case_status = $core.overall_automated_status
        full_50_cases_executed = [int]$fullCases.metrics.executed_cases
        full_50_cases_passed = [int]$fullCases.metrics.passed_cases
        full_50_agent_completeness_rate = $fullCases.metrics.agent_completeness_rate
        core_key_point_proxy_coverage = $fullCases.metrics.core_key_point_proxy_coverage
        difficulty_rule_match_accuracy = $fullCases.metrics.difficulty_rule_match_accuracy
        feedback_decision_accuracy = $fullCases.metrics.feedback_decision_accuracy
        correction_cases = [int]$fullCases.metrics.correction_cases
        correction_demo_status = $correction.status
        expert_review_status = $expert.expert_review_status
        expert_professional_accuracy = $expert.metrics.professional_accuracy
        expert_core_knowledge_coverage = $expert.metrics.core_knowledge_point_coverage
        expert_hallucination_rate = $expert.metrics.hallucination_rate
        expert_difficulty_adaptation_accuracy = $expert.metrics.difficulty_adaptation_accuracy
        expert_signature_status = $expert.reviewer_signature_status
        batch2_20_case_status = $batch2.automated_status
        batch2_retrieval_hit_rate = $batch2.metrics.retrieval_case_hit_rate
        literature_10_case_status = $literature.automated_status
        literature_source_hit_rate = $literature.metrics.source_hit_rate
        literature_traceability_rate = $literature.metrics.evidence_traceability_rate
        literature_review_coverage = $literature.metrics.expert_review_coverage
        literature_boundary_coverage = $literature.metrics.boundary_statement_coverage
        maintenance_6_case_status = $maintenance.automated_status
        maintenance_source_hit_rate = $maintenance.metrics.source_hit_rate
        maintenance_traceability_rate = $maintenance.metrics.evidence_traceability_rate
        maintenance_boundary_coverage = $maintenance.metrics.boundary_statement_coverage
        guided_inquiry_15_case_status = $guided.automated_status
        guided_inquiry_pass_rate = $guided.metrics.pass_rate
        guided_inquiry_evidence_closure_rate = $guided.metrics.evidence_closure_rate
        guided_inquiry_security_control_rate = $guided.metrics.security_control_rate
        guided_inquiry_es_usage_rate = $guided.metrics.elasticsearch_usage_rate
        interface_assistant_39_case_status = $assistant.status
        interface_assistant_case_count = [int]$assistant.metrics.case_count
        interface_assistant_pass_rate = $assistant.metrics.pass_rate
        interface_assistant_routing_accuracy = $assistant.metrics.routing_accuracy
        interface_assistant_evidence_availability = $assistant.metrics.evidence_availability
        interface_assistant_boundary_coverage = $assistant.metrics.boundary_coverage
        interface_assistant_es_pass_rate = $assistantEs.metrics.pass_rate
        interface_assistant_es_evidence_availability = $assistantEs.metrics.evidence_availability
        fallback_flow_status = $fallback.status
        fallback_knowledge_source = $fallback.mode.knowledge_source
        fallback_agent_steps = $fallback.flow.agent_step_count
        fallback_feedback_iteration_steps = $fallback.flow.feedback_iteration_steps
    }
    evidence_files = @(
        "evaluation/automated_results.json",
        "evaluation/full_case_execution_results.json",
        "evaluation/full_case_execution_status.md",
        "evaluation/review_correction_demo.json",
        "evaluation/review_correction_demo.md",
        "evaluation/expert_review_confirmation.json",
        "evaluation/expert_review_confirmation.md",
        "evaluation/batch2_automated_results.json",
        "evaluation/literature_evidence_results.json",
        "evaluation/maintenance_evidence_results.json",
        "evaluation/guided_inquiry_results.json",
        "evaluation/guided_inquiry_summary.md",
        "evaluation/interface_assistant_eval_results.json",
        "evaluation/interface_assistant_eval_summary.md",
        "evaluation/interface_assistant_eval_results_es.json",
        "evaluation/interface_assistant_eval_summary_es.md",
        "evaluation/fallback_acceptance_results.json",
        "submission_materials/03_答辩PPT材料/航空工程材料多智能体训练系统_答辩PPT_正式提交版.pptx"
    )
}

$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $jsonPath

$lines = @(
    "# 最终自动验收报告",
    "",
    "生成时间：``$($report.generated_at)``",
    "",
    "## 验收结论",
    "",
    "**通过。** 当前 SQL + Elasticsearch 工程模式、50 条完整执行、审核纠偏重生、专项测评、后端测试和前端生产构建均正常。",
    "",
    "| 检查项 | 结果 |",
    "| --- | ---: |",
    "| API 版本 | $($report.version) |",
    "| 数据模式 | $($report.mode.data_backend) |",
    "| MySQL | 已连接 |",
    "| Elasticsearch | 已连接 |",
    "| ES 索引文档数 | $($report.engineering.es_document_count) |",
    "| 后端测试 | $($report.engineering.backend_tests_passed) passed |",
    "| 前端生产构建 | passed |",
    "| 核心 50 条自动测评 | $($report.evaluation.core_50_case_status) |",
    "| 核心 50 条完整执行 | $($report.evaluation.full_50_cases_passed)/$($report.evaluation.full_50_cases_executed) |",
    "| 50 条 Agent 完整率 | $([math]::Round($report.evaluation.full_50_agent_completeness_rate * 100, 2))% |",
    "| 核心知识点代理覆盖率 | $([math]::Round($report.evaluation.core_key_point_proxy_coverage * 100, 2))% |",
    "| 难度规则匹配率 | $([math]::Round($report.evaluation.difficulty_rule_match_accuracy * 100, 2))% |",
    "| 反馈决策准确率 | $([math]::Round($report.evaluation.feedback_decision_accuracy * 100, 2))% |",
    "| 审核纠偏重生 | $($report.evaluation.correction_cases) 条；固定案例 $($report.evaluation.correction_demo_status) |",
    "| 专家复核 | $($report.evaluation.expert_review_status)；签字 $($report.evaluation.expert_signature_status) |",
    "| 专业正确率 | $([math]::Round($report.evaluation.expert_professional_accuracy * 100, 2))% |",
    "| 核心知识点语义覆盖率 | $([math]::Round($report.evaluation.expert_core_knowledge_coverage * 100, 2))% |",
    "| 专业幻觉率 | $([math]::Round($report.evaluation.expert_hallucination_rate * 100, 2))% |",
    "| 难度适配准确率 | $([math]::Round($report.evaluation.expert_difficulty_adaptation_accuracy * 100, 2))% |",
    "| 第二批 20 条证据测评 | $($report.evaluation.batch2_20_case_status) |",
    "| 文献证据 10 条专项回归 | $($report.evaluation.literature_10_case_status) |",
    "| FAA 维修证据 6 条专项回归 | $($report.evaluation.maintenance_6_case_status) |",
    "| 动态追问 15 条专项回归 | $($report.evaluation.guided_inquiry_15_case_status)，通过率 $([math]::Round($report.evaluation.guided_inquiry_pass_rate * 100))% |",
    "| 动态追问证据闭合率 | $([math]::Round($report.evaluation.guided_inquiry_evidence_closure_rate * 100))% |",
    "| 动态追问安全控制率 | $([math]::Round($report.evaluation.guided_inquiry_security_control_rate * 100))% |",
    "| 全局助手 39 条专项回归 | $($report.evaluation.interface_assistant_39_case_status)，$($report.evaluation.interface_assistant_case_count)/39，通过率 $([math]::Round($report.evaluation.interface_assistant_pass_rate * 100))% |",
    "| 全局助手意图路由准确率 | $([math]::Round($report.evaluation.interface_assistant_routing_accuracy * 100))% |",
    "| 全局助手领域证据可用率 | $([math]::Round($report.evaluation.interface_assistant_evidence_availability * 100))% |",
    "| 全局助手回答边界覆盖率 | $([math]::Round($report.evaluation.interface_assistant_boundary_coverage * 100))% |",
    "| 全局助手 ES 模式通过率 | $([math]::Round($report.evaluation.interface_assistant_es_pass_rate * 100))% |",
    "| JSON/mock 完整闭环 | $($report.evaluation.fallback_flow_status)，$($report.evaluation.fallback_agent_steps) Agent + $($report.evaluation.fallback_feedback_iteration_steps) 步反馈迭代 |",
    "| 文献来源命中率 | $([math]::Round($report.evaluation.literature_source_hit_rate * 100))% |",
    "| 文献证据可追溯率 | $([math]::Round($report.evaluation.literature_traceability_rate * 100))% |",
    "| 文献卡人工复核覆盖率 | $([math]::Round($report.evaluation.literature_review_coverage * 100))% |",
    "| FAA 维修来源命中率 | $([math]::Round($report.evaluation.maintenance_source_hit_rate * 100))% |",
    "| FAA 维修证据可追溯率 | $([math]::Round($report.evaluation.maintenance_traceability_rate * 100))% |",
    "",
    "> 自动验收不替代正式比赛要求中的专家签字、报名材料核对和演示视频人工检查。"
)
$lines -join "`n" | Set-Content -Encoding utf8 $markdownPath

Copy-Item -LiteralPath $jsonPath -Destination (Join-Path $submissionDir "最终自动验收报告.json") -Force
Copy-Item -LiteralPath $markdownPath -Destination (Join-Path $submissionDir "最终自动验收报告.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\fallback_acceptance_results.json") -Destination (Join-Path $submissionDir "JSON兜底模式验收报告.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\fallback_acceptance_summary.md") -Destination (Join-Path $submissionDir "JSON兜底模式验收报告.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\maintenance_evidence_results.json") -Destination (Join-Path $submissionDir "FAA维修证据专项测评.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\maintenance_evidence_summary.md") -Destination (Join-Path $submissionDir "FAA维修证据专项测评.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\guided_inquiry_results.json") -Destination (Join-Path $submissionDir "动态追问专项测评.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\guided_inquiry_summary.md") -Destination (Join-Path $submissionDir "动态追问专项测评.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\interface_assistant_eval_results.json") -Destination (Join-Path $submissionDir "全局上下文助手专项测评.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\interface_assistant_eval_summary.md") -Destination (Join-Path $submissionDir "全局上下文助手专项测评.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\interface_assistant_eval_results_es.json") -Destination (Join-Path $submissionDir "全局上下文助手ES专项测评.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\interface_assistant_eval_summary_es.md") -Destination (Join-Path $submissionDir "全局上下文助手ES专项测评.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\qwen_interface_assistant_results.json") -Destination (Join-Path $submissionDir "Qwen全局助手真实回答抽样.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\qwen_interface_assistant_summary.md") -Destination (Join-Path $submissionDir "Qwen全局助手真实回答抽样.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\full_case_execution_results.json") -Destination (Join-Path $submissionDir "evaluation\full_case_execution_results.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\full_case_execution_status.md") -Destination (Join-Path $submissionDir "evaluation\full_case_execution_status.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\review_correction_demo.json") -Destination (Join-Path $submissionDir "evaluation\review_correction_demo.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\review_correction_demo.md") -Destination (Join-Path $submissionDir "evaluation\review_correction_demo.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\expert_review_confirmation.json") -Destination (Join-Path $submissionDir "evaluation\expert_review_confirmation.json") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "evaluation\expert_review_confirmation.md") -Destination (Join-Path $submissionDir "evaluation\expert_review_confirmation.md") -Force

Write-Host "Acceptance passed." -ForegroundColor Green
Write-Host "  API version: $($report.version)"
Write-Host "  Database:    connected"
Write-Host "  ES index:    $($report.engineering.es_document_count) documents"
Write-Host "  Evaluation:  full 50 + guided inquiry 15 + interface assistant 39 (JSON + ES) + 20 + 10 + 6 cases, expert review, correction demo and JSON fallback passed"
Write-Host "  Backend:     $testCount tests passed"
Write-Host "  Frontend:    production build passed"
Write-Host "  Report:      $markdownPath"
