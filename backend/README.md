# Backend

FastAPI 后端负责学习者画像、诊断评分、多智能体编排、知识检索、资源生成、学情报告、反馈决策、SQL 持久化和系统健康检查。

## 启动

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## 环境变量

后端读取 `backend/.env`，模板见 `.env.example`。

推荐正式演示：

```env
DATA_BACKEND=sql
DATABASE_ENABLED=true
DATABASE_URL=mysql+pymysql://root:<本机密码>@127.0.0.1:3306/agents

ES_ENABLED=true
ES_URL=http://127.0.0.1:9201
ES_USERNAME=
ES_PASSWORD=
ES_INDEX_KNOWLEDGE=aviation_material_knowledge

LLM_ENABLED=false
```

mock 兜底：

```env
DATA_BACKEND=json
DATABASE_ENABLED=false
ES_ENABLED=false
LLM_ENABLED=false
```

## 主要接口

- `GET /api/health`
- `GET /api/profiles`
- `GET /api/domains`
- `GET /api/questions?domain=tire`
- `GET /api/knowledge/sources`
- `GET /api/knowledge/experiments?domain=brake`
- `POST /api/diagnosis`
- `POST /api/agent/run`
- `POST /api/agent/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/events`
- `POST /api/tasks/{task_id}/cancel`
- `POST /api/tasks/{task_id}/retry`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/resources`
- `GET /api/sessions/{session_id}/report`
- `GET /api/sessions/{session_id}/export`
- `POST /api/sessions/{session_id}/feedback`
- `POST /api/sessions/{session_id}/ask`
- `POST /api/sessions/{session_id}/inquiry-tasks`
- `GET /api/sessions/{session_id}/inquiries`
- `POST /api/assistant/ask`
- `POST /api/assistant/tasks`

`/ask` 不是通用聊天接口。它带入当前会话的学习者画像、诊断薄弱点和学习目标，执行“材料路由 -> RAG 检索 -> 个性化讲解 -> 审核纠偏 -> 路径决策”，并返回证据 ID、边界说明和 5 个 Agent 步骤。

`/assistant/ask` 与 `/assistant/tasks` 为全局上下文助手接口。请求携带当前页面、方向、画像、诊断摘要和可选会话 ID；导航问题即时返回，专业问题复用 5 Agent 证据约束链。无正式会话时只建立临时上下文，不写入学习记录。

`/agent/tasks` 和 `/inquiry-tasks` 是异步任务入口。前端通过 `/tasks/{task_id}/events` 接收 `text/event-stream` 实时事件；每个事件包含 `event_type`、`progress`、`current_agent`、`step_index`、`message`、`detail`、`elapsed_ms` 和 `step_timings`。`step_timings` 记录逐 Agent 的开始时间、完成时间和真实耗时。停止为合作式取消：如果真实模型请求已发出，系统会等待该请求返回，再停止后续 Agent 和正式结果写入。旧同步接口继续保留，用于兼容测试和兜底。

`/api/knowledge/experiments` 返回公开论文与报告提取的实验卡。当前 5 张卡均为 `expert_reviewed`，复核范围限于参数转录、来源定位和适用边界，不代表项目团队重复开展原论文试验。

运行公开文献实验证据专项检索回归：

```powershell
python -m app.evaluation.literature_evidence_runner
```

## `/api/health` 字段

- `backend_status`
- `data_backend`
- `database_enabled`
- `database_connected`
- `es_enabled`
- `es_connected`
- `es_url`
- `es_index`
- `llm_enabled`
- `llm_resource_generation_enabled`
- `llm_semantic_review_enabled`
- `llm_model`
- `knowledge_source`
- `version`

## SQL 迁移与初始化

当前版本使用 Alembic 管理 SQL 表结构。现有 `create_all()` 仅作为兼容兜底；标准初始化顺序如下：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.db.migrate
python -m app.db.seed
```

`python -m app.db.migrate` 对空库执行完整迁移；对已存在的旧版八表数据库，先登记基线再补建 `async_tasks`，不会清空原数据。当前迁移版本为 `20260812_0002`。

启用 SQL 后，完整演示流程会写入：

- `learners`
- `diagnosis_records`
- `agent_sessions`
- `agent_steps`
- `generated_resources`
- `learning_reports`
- `feedback_records`
- `learning_interactions`
- `async_tasks`

`async_tasks` 持久化三个异步入口的事件、进度、结果和原始请求。后端重启后，已完成任务仍可通过原 `task_id` 查询；重启时仍处于排队或运行状态的任务会转为 `interrupted`，前端显示中断原因并允许按原请求重试。

当前已验证：

- `learners: 3`
- `diagnosis_records: 2`
- `agent_sessions: 2`
- `agent_steps: 12`
- `generated_resources: 2`
- `learning_reports: 2`
- `feedback_records: 2`

## Elasticsearch 索引导入

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.search.indexer
```

新增或更新外部 PDF、JATS XML、Zenodo 元数据后，执行完整语料管线：

```powershell
python -m app.rag.pdf_parser
python -m app.rag.structured_parser
python -m app.rag.pipeline
```

来源许可、校验值和本地文件路径登记在 `D:\agents\knowledge_corpus\source_registry.json`。只有资料变化时才需要重建索引，日常启动系统不需要重复执行。

验证：

```powershell
curl.exe http://127.0.0.1:9201/_cat/indices?v
```

当前已验证：索引 `aviation_material_knowledge` 共 1,766 条知识片段，来源登记共 39 条逻辑来源，覆盖公开资料、领域笔记、团队授权实验和 17 条人工整理基础片段。

## LLM 模式

稳定兜底模式：

```env
LLM_ENABLED=false
```

真实 LLM 增强模式：

```env
LLM_ENABLED=true
LLM_RESOURCE_GENERATION_ENABLED=false
LLM_SEMANTIC_REVIEW_ENABLED=false
LLM_BASE_URL=https://your-api.example.com/v1
LLM_API_KEY=your_key
LLM_MODEL=your_model
LLM_TIMEOUT=60
LLM_MAX_TOKENS=1800
LLM_RETRIES=1
```

`LLM_BASE_URL` 填 OpenAI-compatible API 的版本根路径，例如 `https://provider.example/v1`。云端服务通常需要 `LLM_API_KEY`；本地兼容服务允许留空。正式演示建议保持 `LLM_RESOURCE_GENERATION_ENABLED=false` 与 `LLM_SEMANTIC_REVIEW_ENABLED=false`：智能助手和训练追问仍调用真实 LLM，讲义等资源使用可复现模板，审核 Agent 使用确定性证据闭合和边界规则，避免重复模型调用影响诊断与反馈闭环。需要单独评测全量 LLM 资源生成或双模型语义审核时再将对应开关设为 `true`，输出不合格时仍会自动回退。动态追问返回 `generation_audit` 和 `review_audit`，记录模型、提示词版本、耗时、调用结果和脱敏后的回退原因。

Qwen 已验证配置使用 `https://dashscope.aliyuncs.com/compatible-mode/v1` 与 `qwen-plus`。结构化请求启用 JSON Object 模式且不设置 `max_tokens`，以避免完整资源 JSON 被截断；普通文本请求仍使用 `LLM_MAX_TOKENS`。本地 `.env` 已被 `.gitignore` 排除，`.env.example` 不包含真实密钥。

## 测试

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
pytest
```

当前稳定性修复基线：`116 passed`。提交前以本机最新 `pytest` 输出、`competition_baseline.json` 和 `CURRENT_ACCEPTANCE_SUMMARY.md` 为准。

评测摘要接口：`GET /api/evaluation/summary`，返回 50 条主流程结果、15 条动态追问专项结果、机器辅助指标、专家复核状态和签字状态。

动态追问专项测评：

```powershell
python -m app.evaluation.guided_inquiry_runner --use-es
```

结果写入 `evaluation/guided_inquiry_results.json` 和 `evaluation/guided_inquiry_summary.md`。

团队实验模板校验：

```powershell
python -m app.rag.team_dataset_validator
```

团队实验模板转换预演（不注册、不入 ES）：

```powershell
python -m app.rag.team_dataset_pipeline --dry-run-template
```

真实数据完成脱敏、授权和专业审核后，执行正式转换和索引：

```powershell
python -m app.rag.team_dataset_pipeline --ingest --index
```

`--ingest` 是显式安全闸门：缺少正式 manifest、审核未通过、未授权或包含 `DEMO-*` 记录时均会失败。Excel 读取依赖 `openpyxl==3.1.5`，安装依赖仍使用 `pip install -r requirements.txt`。

模板目录为 `D:\agents\knowledge_corpus\raw_docs\team_tire`。没有真实 manifest 或授权/复核未通过时，校验器保持 `approved_for_rag=false`，不会写入正式知识库。

测试覆盖：

- 诊断评分逻辑。
- JSON 检索 fallback。
- SQL 写入。
- ES 优先检索与 fallback。
- mock 生成与 LLM 失败 fallback。
- Orchestrator 完整输出 6 个 Agent 步骤。
# 团队实验多模态证据接口

实验资产清单位于 `D:\agents\knowledge_corpus\experimental_assets\catalog.json`。运行中的后端不读取移动硬盘绝对路径，只返回脱敏来源和项目内衍生媒体。

主要接口：

- `GET /api/evidence/assets`：列出资产，可用 `topic`、`evidence_ids` 或 `source_ids` 筛选；
- `GET /api/evidence/assets/{asset_id}`：获取单项工况、标签、审核状态和溯源信息；
- `GET /api/evidence/assets/{asset_id}/media`：读取项目内缩略图或趋势图；
- `GET /api/health`：`experimental_evidence` 返回专题数、资产数和已审核数量。

需要从授权源资料重新生成时执行：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.rag.import_experimental_assets
python -m app.rag.pipeline
```

导入器会读取 `E:\梁永琦` 与 `H:\任孝琴` 中已授权并完成映射的实验资料。当前会生成：

- 10项实胎偏磨资产；
- 15项热氧老化多模态资产；
- 12项紫外老化后摩擦形貌资产；
- 15项载荷-距离矩阵光学图像与1张趋势图；
- 两份第二批 RAG 专题 Markdown 和20条专项测评用例。

导入器只在项目中保留缩略图、结构化工况和 SHA-256。紫外摩擦参数无法唯一核对时保持待确认；载荷-距离专题的温升字段保持部分证据状态。完成导入和 RAG pipeline 后，移动硬盘可以断开，不影响 API 和演示流程。



