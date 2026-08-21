param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://127.0.0.1:5173",
    [string]$EsUrl = "http://127.0.0.1:9201",
    [switch]$WarmDemo,
    [switch]$WarmLlm,
    [int]$HttpTimeoutSeconds = 12,
    [int]$PipelineTimeoutSeconds = 210
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$baselinePath = Join-Path $projectRoot "competition_baseline.json"
$outputDir = Join-Path $projectRoot "outputs\demo"
$outputPath = Join-Path $outputDir "demo_preflight_latest.json"
$apiBase = "$BackendUrl/api"
$checks = @()

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $script:checks += [ordered]@{ name = $Name; passed = $Passed; detail = $Detail }
    $color = if ($Passed) { "Green" } else { "Red" }
    $mark = if ($Passed) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1}: {2}" -f $mark, $Name, $Detail) -ForegroundColor $color
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body = $null,
        [int]$TimeoutSec = $HttpTimeoutSeconds
    )
    $params = @{
        Method = $Method
        Uri = $Uri
        TimeoutSec = $TimeoutSec
        UseBasicParsing = $true
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json; charset=utf-8"
        $json = $Body | ConvertTo-Json -Depth 20 -Compress
        $tempBody = New-TemporaryFile
        try {
            $json | Set-Content -LiteralPath $tempBody.FullName -Encoding UTF8 -NoNewline
            $params.InFile = $tempBody.FullName
            $response = Invoke-WebRequest @params
        }
        finally {
            Remove-Item -LiteralPath $tempBody.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        $response = Invoke-WebRequest @params
    }

    $response.RawContentStream.Position = 0
    $reader = New-Object System.IO.StreamReader(
        $response.RawContentStream,
        [System.Text.Encoding]::UTF8,
        $true
    )
    try {
        return $reader.ReadToEnd() | ConvertFrom-Json
    }
    finally {
        $reader.Dispose()
    }
}

function Wait-ManagedTask {
    param([string]$TaskId, [int]$TimeoutSec = $PipelineTimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $lastState = ""
    while ((Get-Date) -lt $deadline) {
        $snapshot = Invoke-Json "GET" "$apiBase/tasks/$TaskId" $null $HttpTimeoutSeconds
        $state = "$($snapshot.status)|$($snapshot.progress)|$($snapshot.current_agent)"
        if ($state -ne $lastState) {
            Write-Host ("  task {0}% [{1}] {2}" -f $snapshot.progress, $snapshot.status, $snapshot.current_agent) -ForegroundColor DarkGray
            $lastState = $state
        }
        if ($snapshot.status -in @("completed", "failed", "cancelled", "interrupted")) {
            return $snapshot
        }
        Start-Sleep -Milliseconds 800
    }
    throw "Managed task timed out after $TimeoutSec seconds: $TaskId"
}

Write-Host "Demo preflight: read-only checks" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $python)) {
    Add-Check "Backend Python" $false "missing: $python"
}
else {
    Add-Check "Backend Python" $true $python
}

if (-not (Test-Path -LiteralPath $baselinePath)) {
    Add-Check "Competition baseline" $false "missing: $baselinePath"
}
else {
    $baseline = Get-Content -LiteralPath $baselinePath -Raw -Encoding UTF8 | ConvertFrom-Json
    & $python (Join-Path $projectRoot "scripts\check_competition_baseline.py") *> $null
    Add-Check "Competition baseline" ($LASTEXITCODE -eq 0) "expected ES=$($baseline.knowledge.indexed_chunks), tests=$($baseline.engineering.backend_tests_passed)"
}

$dockerReady = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    & cmd.exe /d /c "docker info >nul 2>&1"
    $dockerReady = $LASTEXITCODE -eq 0
}
Add-Check "Docker Engine" $dockerReady $(if ($dockerReady) { "running" } else { "start Docker Desktop, then run scripts/start_project.ps1" })

if ($dockerReady) {
    foreach ($container in @("report-mysql", "agents-es")) {
        $status = docker inspect --format "{{.State.Status}}" $container 2>$null
        Add-Check "Container $container" ($status -eq "running") $(if ($status) { $status } else { "not found" })
    }
}

$health = $null
try {
    $health = Invoke-Json "GET" "$apiBase/health"
    Add-Check "Backend health" ($health.backend_status -eq "ok") "version=$($health.version)"
    Add-Check "MySQL connection" ([bool]$health.database_connected) "enabled=$($health.database_enabled), backend=$($health.data_backend)"
    Add-Check "Elasticsearch connection" ([bool]$health.es_connected) "mode=$($health.retrieval_mode), source=$($health.knowledge_source)"
    Add-Check "Async task store" ([bool]$health.async_tasks.table_ready) "persistent=$($health.async_tasks.persistence_enabled)"
}
catch {
    Add-Check "Backend health" $false $_.Exception.Message
}

try {
    Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec $HttpTimeoutSeconds | Out-Null
    Add-Check "Frontend" $true $FrontendUrl
}
catch {
    Add-Check "Frontend" $false $_.Exception.Message
}

if ($health -and $health.es_connected) {
    try {
        $esCount = Invoke-Json "GET" "$EsUrl/$($health.es_index)/_count"
        $expected = [int]$baseline.knowledge.indexed_chunks
        Add-Check "ES document count" ([int]$esCount.count -eq $expected) "actual=$($esCount.count), expected=$expected"
    }
    catch {
        Add-Check "ES document count" $false $_.Exception.Message
    }
}

try {
    $profiles = Invoke-Json "GET" "$apiBase/profiles"
    $domains = Invoke-Json "GET" "$apiBase/domains"
    $questions = Invoke-Json "GET" "$apiBase/questions?domain=tire"
    $demos = Invoke-Json "GET" "$apiBase/demo-sessions"
    Add-Check "Demo seed data" (@($profiles).Count -ge 3 -and @($domains).Count -ge 3 -and @($questions).Count -ge 5 -and @($demos).Count -ge 1) "profiles=$(@($profiles).Count), domains=$(@($domains).Count), tire_questions=$(@($questions).Count), demos=$(@($demos).Count)"
}
catch {
    Add-Check "Demo seed data" $false $_.Exception.Message
}

$warmSessionId = $null
if ($WarmDemo) {
    Write-Host "Demo preflight: warming the full closed loop" -ForegroundColor Cyan
    try {
        $demo = @($demos)[0]
        $diagnosis = Invoke-Json "POST" "$apiBase/diagnosis" @{
            profile_id = $demo.profile_id
            domain = $demo.domain
            answers = @($demo.diagnosis_answers)
        } $PipelineTimeoutSeconds
        Add-Check "Warm diagnosis" ($null -ne $diagnosis.score) "score=$($diagnosis.score), level=$($diagnosis.level)"

        $task = Invoke-Json "POST" "$apiBase/agent/tasks" @{
            profile_id = $demo.profile_id
            domain = $demo.domain
            diagnosis_result = $diagnosis
            learning_goal = $demo.learning_goal
        } $PipelineTimeoutSeconds
        $task = Wait-ManagedTask $task.task_id $PipelineTimeoutSeconds
        if ($task.status -ne "completed") {
            throw "Agent task ended with status=$($task.status): $($task.error)"
        }
        $run = $task.result
        $warmSessionId = $run.session_id
        Add-Check "Warm 6-Agent pipeline" (@($run.agent_steps).Count -eq 6) "session=$warmSessionId, steps=$(@($run.agent_steps).Count), elapsed_ms=$($task.elapsed_ms)"

        $resources = Invoke-Json "GET" "$apiBase/sessions/$warmSessionId/resources" $null $HttpTimeoutSeconds
        $report = Invoke-Json "GET" "$apiBase/sessions/$warmSessionId/report" $null $HttpTimeoutSeconds
        $feedback = Invoke-Json "POST" "$apiBase/sessions/$warmSessionId/feedback" @{
            answers = @()
            self_feedback = "演示预检自动提交，不作为正式学习记录。"
        } $PipelineTimeoutSeconds
        $resourceReady = $resources.personalized_lecture -and $resources.practical_guide -and $resources.graded_quiz -and $resources.case_task
        Add-Check "Warm resources and report" ([bool]$resourceReady -and $null -ne $report) "resources=4, feedback_action=$($feedback.next_action)"
    }
    catch {
        Add-Check "Warm closed loop" $false $_.Exception.Message
    }
}

if ($WarmLlm) {
    Write-Host "Demo preflight: warming the optional LLM path" -ForegroundColor Cyan
    if (-not $health.llm_enabled -or -not $health.llm_configured) {
        Add-Check "LLM warm-up" $false "LLM is not enabled/configured; use SQL + ES + mock for recording"
    }
    else {
        try {
            $assistant = Invoke-Json "POST" "$apiBase/assistant/ask" @{
                question = "Explain why a tire damage decision cannot rely on one photo only."
                context = @{
                    active_view = "home"
                    active_view_label = "Home"
                    domain = "tire"
                    profile_id = "undergrad_basic"
                    learner_type = "undergraduate"
                    learning_goal = "Understand thermo-oxidative aging and sliding wear."
                    session_id = $warmSessionId
                }
            } $PipelineTimeoutSeconds
            Add-Check "LLM warm-up" ($assistant.generation_mode -eq "llm") "mode=$($assistant.generation_mode), source=$($assistant.knowledge_source)"
        }
        catch {
            Add-Check "LLM warm-up" $false "$($_.Exception.Message); switch LLM_ENABLED=false for recording"
        }
    }
}

$failed = @($checks | Where-Object { -not $_.passed })
$result = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($failed.Count -eq 0) { "ready" } else { "needs_attention" }
    warm_demo = [bool]$WarmDemo
    warm_llm = [bool]$WarmLlm
    warm_session_id = $warmSessionId
    checks = $checks
}
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outputPath -Encoding UTF8

Write-Host "Report: $outputPath" -ForegroundColor DarkGray
if ($failed.Count -gt 0) {
    Write-Host "Demo preflight NEEDS ATTENTION ($($failed.Count) failed checks)." -ForegroundColor Yellow
    exit 1
}
Write-Host "Demo preflight READY." -ForegroundColor Green
exit 0
