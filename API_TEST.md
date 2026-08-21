# API_TEST

以下命令适合在 PowerShell 中执行。请先启动后端：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 1. 健康检查

```powershell
$health = Invoke-RestMethod http://127.0.0.1:8000/api/health
$health | ConvertTo-Json -Depth 8
```

工程模式下重点查看：

```powershell
$health.data_backend
$health.database_connected
$health.es_connected
$health.knowledge_source
$health.llm_enabled
```

预期：

- `data_backend = sql`
- `database_connected = true`
- `es_connected = true`
- `knowledge_source = elasticsearch`
- `llm_enabled = false`

## 1.1 获取评测与专家复核摘要

```powershell
$evaluation = Invoke-RestMethod http://127.0.0.1:8000/api/evaluation/summary
$evaluation | ConvertTo-Json -Depth 8
```

预期：

- `core_cases.passed = 50`
- `core_cases.total = 50`
- `expert_review.confirmed = true`
- `expert_review.professional_accuracy = 1`
- `expert_review.hallucination_rate = 0`
- `expert_review.signature_status = electronic_confirmation_recorded`

## 2. 获取学习者画像

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/profiles | ConvertTo-Json -Depth 6
```

## 3. 获取材料方向

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/domains | ConvertTo-Json -Depth 6
```

## 4. 获取诊断题

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/questions?domain=tire" | ConvertTo-Json -Depth 6
```

## 5. 提交诊断结果

```powershell
$questions = Invoke-RestMethod "http://127.0.0.1:8000/api/questions?domain=tire"
$answers = @()
foreach ($q in $questions) {
  $answers += @{
    question_id = $q.id
    answer = $q.answer
  }
}

$diagnosisBody = @{
  profile_id = "undergrad_basic"
  domain = "tire"
  answers = $answers
} | ConvertTo-Json -Depth 8

$diagnosis = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/diagnosis" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $diagnosisBody

$diagnosis | ConvertTo-Json -Depth 8
```

## 6. 运行多智能体闭环

```powershell
$agentBody = @{
  profile_id = "undergrad_basic"
  domain = "tire"
  diagnosis_result = $diagnosis
  learning_goal = "理解航空轮胎热氧老化与滑动磨损损伤机理，并能完成基本损伤判读。"
} | ConvertTo-Json -Depth 12

$agentRun = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/agent/run" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $agentBody

$agentRun | ConvertTo-Json -Depth 12
$sessionId = $agentRun.session_id
```

Agent 步骤应包含 6 个 Agent。RetrievalAgent 在 ES 可用时应显示检索来源为 `elasticsearch`。

### 6.1 异步任务与真实进度

```powershell
$task = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/agent/tasks" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $agentBody

$taskId = $task.task_id
Invoke-WebRequest "http://127.0.0.1:8000/api/tasks/$taskId/events"
$taskStatus = Invoke-RestMethod "http://127.0.0.1:8000/api/tasks/$taskId"
$taskStatus | Select-Object status, progress, elapsed_ms
$taskStatus.step_timings | Format-Table step_index, agent_name, duration_ms, status
$taskStatus | ConvertTo-Json -Depth 12
```

完成后应看到 `elapsed_ms` 和 6 条 `step_timings`；动态追问任务对应 5 条 Agent 耗时记录。

取消与重试：

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/tasks/$taskId/cancel"
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/tasks/$taskId/retry"
```

历史会话与完整恢复快照：

```powershell
$history = Invoke-RestMethod "http://127.0.0.1:8000/api/sessions?limit=12"
$history.items | Format-Table session_id, profile_id, domain, diagnosis_score, interaction_count
Invoke-RestMethod "http://127.0.0.1:8000/api/sessions/$sessionId" | ConvertTo-Json -Depth 12
```

## 7. 获取个性化资源

```powershell
$resources = Invoke-RestMethod "http://127.0.0.1:8000/api/sessions/$sessionId/resources"
$resources | ConvertTo-Json -Depth 12
```

## 8. 获取学情报告

```powershell
$report = Invoke-RestMethod "http://127.0.0.1:8000/api/sessions/$sessionId/report"
$report | ConvertTo-Json -Depth 12
```

## 9. 导出学情报告

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/sessions/$sessionId/export" `
  -OutFile ".\learning-report-$sessionId.md"
```

## 10. 提交反馈测试

```powershell
$quiz = $resources.graded_quiz
$feedbackAnswers = @()
foreach ($item in $quiz) {
  $feedbackAnswers += @{
    question_id = $item.id
    answer = $item.answer
  }
}

$feedbackBody = @{
  answers = $feedbackAnswers
  self_feedback = "希望继续通过案例巩固胎面裂纹和剥落判读。"
} | ConvertTo-Json -Depth 8

$feedback = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/sessions/$sessionId/feedback" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $feedbackBody

$feedback | ConvertTo-Json -Depth 8
```

## 10.1 提交启发式动态追问

完成第 6 步并取得 `$sessionId` 后执行：

```powershell
$askBody = @{
  question = "为什么在 60 N、160 m 往复摩擦工况下，不能只凭磨损形貌就断定热氧老化是主导机制？"
} | ConvertTo-Json

$inquiry = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/sessions/$sessionId/ask" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $askBody

$inquiry | ConvertTo-Json -Depth 10
```

重点核对：

```powershell
$inquiry.generation_mode
$inquiry.retrieval_mode
$inquiry.knowledge_source
$inquiry.evidence_ids
$inquiry.review.status
$inquiry.generation_audit
$inquiry.agent_steps.Count
```

`generation_mode=llm` 表示真实模型调用和结构校验成功；`mock-template` 表示主动使用稳定兜底；`mock-template-fallback` 表示模型调用或输出校验失败后自动回退。

读取追问历史：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/sessions/$sessionId/inquiries" |
  ConvertTo-Json -Depth 10
```

再次获取学情报告并导出时，应能看到本轮动态追问：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/sessions/$sessionId/report" |
  Select-Object -ExpandProperty guided_inquiries |
  ConvertTo-Json -Depth 10

Invoke-WebRequest "http://127.0.0.1:8000/api/sessions/$sessionId/export" `
  -OutFile ".\learning-report-with-inquiry.md"
```

动态追问专项测评：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.guided_inquiry_runner --use-es
```

## 11. 获取公开文献实验卡

```powershell
# 全部实验卡
Invoke-RestMethod "http://127.0.0.1:8000/api/knowledge/experiments" |
  ConvertTo-Json -Depth 10

# 仅查看航空制动实验卡，可选 tire / brake / composite
Invoke-RestMethod "http://127.0.0.1:8000/api/knowledge/experiments?domain=brake" |
  ConvertTo-Json -Depth 10
```

返回结果应包含 `evidence_type=published_literature_experiment`、`review_status=expert_reviewed` 和 `reviewed_count=5`；每条记录应带有 `evidence_ids`、`source_locators`、`source_url`、`limitations`、`reviewed_at` 和 `review_scope`。

专项检索回归：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.literature_evidence_runner
```

预期 `automated_status=passed`，五项指标均为 `1.0`。

## 12. SQL seed

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.db.seed
```

## 13. Elasticsearch 导入知识库

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.search.indexer
```

## 14. Elasticsearch 索引验证

```powershell
curl.exe http://127.0.0.1:9201/_cat/indices?v
curl.exe http://127.0.0.1:9201/aviation_material_knowledge/_count
```

## 15. Docker 容器检查

```powershell
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

## 16. 全局上下文智能助手

首页操作引导：

```powershell
$body = @{
  question = "我第一次使用应该从哪里开始？"
  context = @{
    active_view = "home"
    active_view_label = "首页"
    domain = "tire"
    profile_id = "undergrad_basic"
    learner_type = "本科低年级学生"
    learning_goal = "理解航空轮胎热氧老化与滑动磨损"
    visible_summary = "首页展示 SQL、ES、LLM 和知识资产状态。"
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/assistant/ask" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body | ConvertTo-Json -Depth 8
```

专业问题异步入口：

```powershell
$body = @{
  question = "热氧老化为什么会影响后续滑动磨损表现？"
  context = @{
    active_view = "diagnosis"
    active_view_label = "学情诊断"
    domain = "tire"
    profile_id = "undergrad_basic"
    learner_type = "本科低年级学生"
    learning_goal = "理解航空轮胎热氧老化与滑动磨损"
  }
} | ConvertTo-Json -Depth 6

$task = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/assistant/tasks" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body

Invoke-RestMethod "http://127.0.0.1:8000/api/tasks/$($task.task_id)" |
  ConvertTo-Json -Depth 10
```

当前学情快速解释（只使用页面已确认数据，不调用完整领域生成链）：

```powershell
$body = @{
  question = "我当前的知识薄弱点是什么？"
  context = @{
    active_view = "report"
    active_view_label = "学情报告"
    domain = "tire"
    profile_id = "undergrad_basic"
    learner_type = "本科低年级学生"
    diagnosis_score = 62
    diagnosis_level = "基础"
    weak_points = @("热氧老化", "实验表征")
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/assistant/ask" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body | ConvertTo-Json -Depth 8
```

全局上下文助手 15 条专项测评：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.interface_assistant_runner
```

当前结果：15/15 通过；意图路由、Agent 完整性、关键内容、领域证据可用性和回答边界覆盖率均为 100%。

## 17. 后端测试

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
pytest
```

当前结果：`116 passed`。

## 18. 前端构建

```powershell
cd D:\agents\frontend
npm run build
```

当前结果：通过。

## 19. 回退 mock / JSON 兜底模式

修改 `backend/.env`：

```env
DATABASE_ENABLED=false
DATA_BACKEND=json
ES_ENABLED=false
LLM_ENABLED=false
```

重启后端即可。接口路径不变，前端流程不变。
# 团队实验多模态证据测试

## 查看证据目录状态

```powershell
$health = Invoke-RestMethod "http://127.0.0.1:8000/api/health"
$health.experimental_evidence | ConvertTo-Json -Depth 5
```

预期：`asset_count=25`、`topic_count=2`、`reviewed_count=25`。

## 查询实胎偏磨专题

```powershell
$assets = Invoke-RestMethod "http://127.0.0.1:8000/api/evidence/assets?topic=service_tire_wear&limit=10"
$assets | ConvertTo-Json -Depth 8
```

## 查询热氧老化专题

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/evidence/assets?topic=thermal_aging_multimodal&limit=15" |
  ConvertTo-Json -Depth 8
```

## 下载一项证据媒体

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/evidence/assets/RXQ-THERMAL-TREND-01/media" `
  -OutFile ".\RXQ-THERMAL-TREND-01.png"
```

## 按RAG证据ID解析实验资产

```powershell
$evidenceId = "team_tire_rxq_aging_multimodal_evidence-c002-6b120286"
Invoke-RestMethod "http://127.0.0.1:8000/api/evidence/assets?evidence_ids=$evidenceId&limit=4" |
  ConvertTo-Json -Depth 8
```



