# 作品设计实现方案

## 1. 项目背景

航空工程材料在服役过程中会受到热、氧、摩擦、冲击、疲劳和复杂环境的共同影响，损伤形式包括航空轮胎胎面橡胶热氧老化与滑动磨损、航空刹车片高温摩擦与热衰退、复合材料板冲击分层与纤维断裂等。该类知识具有专业性强、证据链复杂、实操边界严格的特点。传统教材、单次课堂讲解或普通问答式系统难以同时满足学习者画像识别、知识盲区定位、个性化资源生成、专业审核和动态反馈迭代等训练需求。

本项目面向“领域知识个性化生成与多智能体协同决策系统研究”赛题，构建一套航空工程材料损伤分析训练系统，重点体现垂直领域知识库、多智能体协同闭环、工程化持久化与可检索能力。

## 2. 作品名称

《面向航空工程材料损伤分析的多智能体个性化知识生成与实操训练系统》

## 3. 应用场景

系统面向航空工程材料损伤分析技能培训，第一版覆盖三个方向：

1. 航空轮胎胎面橡胶损伤分析：热氧老化、滑动磨损、胎面裂纹、剥落、损伤等级判读、起降次数影响和磨损形貌分析。
2. 航空刹车片摩擦磨损与失效分析：高温摩擦、热衰退、氧化、裂纹、摩擦性能变化和失效机理。
3. 飞机复合材料板损伤分析：冲击损伤、分层、基体开裂、纤维断裂、无损检测图像判读和损伤扩展。

## 4. 目标用户

- 本科低年级学生：基础概念薄弱，实验经验少，需要降维解释和案例引导。
- 材料方向研究生：具备材料基础，需要深入损伤机理、实验表征和科研分析。
- 科研训练新手：需要把文献知识、实验记录和损伤判读任务连接起来。
- 机务维修新员工：关注损伤检查流程、维护判读和实操规范。

## 5. 系统总体架构

系统采用前后端分离架构：

- 前端层：React + Vite，负责学习者画像输入、诊断答题、Agent 流程展示、资源展示、报告展示和导出。
- 接口层：FastAPI REST API，负责统一对外提供画像、题库、诊断、Agent 编排、资源、报告、反馈和健康检查接口。
- 智能体层：六个 Agent 组成“分析 -> 生成 -> 校验 -> 决策”闭环。
- 数据层：MySQL 用于学习过程持久化，Elasticsearch 用于领域知识库检索，本地 JSON 作为 seed 数据和 fallback 数据。
- 模型层：真实 Qwen 用于证据约束动态问答，主训练资源采用稳定证据模板；OpenAI-compatible 调用失败时自动回退。

## 6. 前端架构

前端保持比赛演示的稳定主线：

1. 首页展示作品定位、训练方向和系统运行状态。
2. “加载演示案例”自动填充本科低年级学生、航空轮胎方向和学习目标。
3. 学习者画像页支持选择画像、方向和目标。
4. 学情诊断页从后端读取题目并提交答案。
5. Agent 流程页展示六个 Agent 的输入、输出、状态、置信度和证据 ID。
6. 资源页展示讲义、实操指南、分阶测试题和案例任务。
7. 学情报告页展示知识盲区、资源难度匹配、学习路径和审核意见。
8. 反馈迭代模块根据测试正确率展示下一步动作。

首页状态区域从 `/api/health` 获取：

- 数据模式：JSON / SQL
- 数据库连接：已连接 / 未连接 / 未启用
- 检索模式：本地规则 / Elasticsearch
- ES 连接：已连接 / 未连接 / 未启用
- 生成模式：Mock / LLM

## 7. 后端架构

后端基于 FastAPI，主要模块包括：

- `app/api/routes.py`：REST API 路由。
- `app/core/config.py`：环境变量配置，固定读取 `backend/.env`。
- `app/services/`：数据加载、诊断评分、资源生成、报告和反馈服务。
- `app/agents/`：六个 Agent 与 orchestrator。
- `app/db/`：SQLAlchemy 数据库连接、ORM 模型、仓储层和 seed 脚本。
- `app/search/`：Elasticsearch 客户端、索引导入器和检索器。
- `app/llm/`：OpenAI-compatible LLM 客户端和提示词模板。
- `app/data/`：本地 JSON 学习者画像、题库、知识库和演示会话。

## 8. 本地 JSON 知识库设计

本地 JSON 仍作为 seed 与 fallback 数据。每条知识片段包含：

- `id`
- `domain`
- `title`
- `tags`
- `difficulty`
- `content`
- `source_type`
- `applicable_learners`
- `common_misconceptions`

JSON 数据覆盖航空轮胎、航空刹车片、复合材料板三个方向。即使 MySQL 或 ES 不可用，系统也能通过 JSON 完成演示闭环。

## 9. 学习者画像设计

学习者画像包含：

- 画像编号
- 名称
- 学习者类型
- 专业背景
- 画像特点
- 默认学习目标
- 自评基础
- 推荐训练方向

当前内置 3 组画像，并已通过 seed 写入 MySQL `learners` 表。

## 10. 多智能体协同机制

系统通过 orchestrator 串联六个 Agent：

1. 学情诊断 Agent：读取画像和诊断结果，输出基础水平、薄弱点和强项。
2. 材料领域路由 Agent：根据训练方向选择航空轮胎、航空刹车片或复合材料知识库。
3. 专业知识检索 Agent：根据薄弱点、学习目标和画像类型检索知识依据。
4. 个性化资源生成 Agent：生成讲义、实操指南、分阶测试题和案例任务。
5. 专家审核纠偏 Agent：检查专业概念、依据一致性、难度匹配和实操约束。
6. 学习路径决策 Agent：输出学习路径、难度匹配、下一步训练计划和推荐动作。

每个 Agent 步骤均包含：

- `agent_name`
- `role`
- `input_summary`
- `output_summary`
- `status`
- `confidence`
- `evidence_ids`
- `details`

## 11. MySQL 持久化设计

在 SQL + ES 工程模式下，系统通过 SQLAlchemy 写入 MySQL。当前表设计包括：

- `learners`：学习者画像。
- `diagnosis_records`：诊断得分、等级、薄弱点、强项和摘要。
- `agent_sessions`：一次完整 Agent 管线会话。
- `agent_steps`：六个 Agent 的中间输出。
- `generated_resources`：讲义、实操指南、分阶测试题和案例任务。
- `learning_reports`：学情报告 Markdown、知识盲区、学习路径、下一步计划和审核意见。
- `feedback_records`：反馈分数、学习者自评、下一步动作和更新后的学习路径。

当前使用 Alembic 管理 SQL 表结构，迁移链为 `20260812_0001`（学习闭环基础表）到 `20260812_0002`（异步任务持久化）。空库执行完整升级；旧版八表数据库先登记基线，再增量创建 `async_tasks`。`create_all()` 仅保留在 seed 与数据库不可迁移时的兼容路径中。

## 12. Elasticsearch 知识库检索设计

系统新增 Elasticsearch 知识库检索层，索引名为：

```text
aviation_material_knowledge
```

索引字段包括：

- `id`
- `domain`
- `title`
- `tags`
- `difficulty`
- `content`
- `source_type`
- `applicable_learners`
- `common_misconceptions`

检索输入包括训练方向、薄弱点、学习目标和画像类型。`ES_ENABLED=true` 且 ES 可用时，RetrievalAgent 优先使用 Elasticsearch；如果 ES 未启用、连接失败或检索异常，自动回退本地 JSON。

第七阶段新增 `knowledge_corpus/` 目录，记录从原始资料、Markdown 解析、切片 JSON 到 ES 索引的证据链。当前语料覆盖公开论文、FAA/NASA/NTSB 报告、开放数据集元数据与已授权课题组轮胎资料；课题组资料已形成 4 个轮胎专题、53 项已审核资产。制动与复合材料当前没有团队实验数据，系统从公开论文和报告中提取 5 张“公开文献实验卡”，记录试样、设备、工况、观测指标、结论、证据 ID 和限制说明。5 张卡均已完成人工复核，复核范围为参数转录、来源定位和适用边界，不代表重复开展原论文试验。FAA-H-8083-31B（2023）复材 NDI 与航空刹车检查维护摘录新增 81 条官方一手切片，使“机理证据”和“操作边界”分层。`index_manifest.json` 记录 1,766 条知识片段的来源、领域、标题、标签、难度、章节或页码定位和入库状态；前端“知识证据库”通过 `/api/knowledge/sources` 与 `/api/knowledge/experiments` 展示来源登记、实验卡、复核状态、切片计数和原始入口。

公开文献实验证据专项回归包含 10 条查询，覆盖 5 张实验卡及三类材料方向。当前真实 Elasticsearch 运行结果为：文献来源 Top-5 命中率 100%、evidence_id 可追溯率 100%、实验卡人工复核覆盖率 100%、适用边界说明覆盖率 100%、Elasticsearch 使用率 100%。结果保存在 `evaluation/literature_evidence_results.json` 与 `evaluation/literature_evidence_summary.md`。

FAA 维修训练证据专项回归包含 6 条查询，覆盖复材敲击/超声/多方法检查和刹车衬片/放气/过热后检查。当前真实 Elasticsearch 结果中，来源命中、证据追溯、官方来源标识、边界说明和 ES 使用率均为 100%。结果保存在 `evaluation/maintenance_evidence_results.json` 与 `evaluation/maintenance_evidence_summary.md`。

## 12.1 RAG 切片与混合检索增强

新增 RAG 模块：

- `backend/app/rag/chunker.py`：按 Markdown 标题、段落和固定长度切片。
- `backend/app/rag/embedder.py`：预留 BGE embedding 接口，默认关闭。
- `backend/app/rag/pipeline.py`：串联 parsed_docs -> chunks -> embeddings -> ES index。

新增环境变量：

```env
BGE_ENABLED=false
BGE_MODEL_PATH=
EMBEDDING_BACKEND=none
RETRIEVAL_MODE=hybrid
```

检索模式：

- `bm25`：Elasticsearch 关键词检索；
- `vector`：BGE 或开发 embedding 语义检索；
- `hybrid`：BM25 与向量结果融合。

当前正式演示在无 BGE 时自动使用 `hybrid-bm25-only`，不影响 SQL + ES 主流程。若提供 BGE 模型路径，可作为技术扩展启用。

BM25 候选结果增加来源多样性重排，在候选充分时限制同一 `source_id` 最多占两个证据位，减少单篇长文垄断前五条证据的问题，使规范、论文、案例和实验记录能够共同参与生成与审核。

## 13. JSON fallback 机制

系统保留 JSON fallback 的原因：

1. 保证比赛现场即使数据库或 ES 异常，也能完整演示。
2. 方便后续通过 JSON 维护 seed 数据和测试数据。
3. 让 mock/JSON 模式与 SQL/ES 模式共用同一套接口路径，避免前端大改。

外部服务连接采用有界等待：MySQL/PostgreSQL 连接与连接池等待上限为 3 秒，Elasticsearch 请求超时为 3 秒且关闭自动重试。Docker Desktop 未运行时，系统已验证可返回离线状态，并完成诊断、6 Agent、JSON fallback 检索、四类资源、报告导出和反馈迭代。

备用演示配置：

```env
DATABASE_ENABLED=false
DATA_BACKEND=json
ES_ENABLED=false
LLM_ENABLED=false
```

## 14. mock LLM 与真实 LLM 受控调用

当前正式演示推荐：

```env
LLM_ENABLED=true
LLM_RESOURCE_GENERATION_ENABLED=false
LLM_SEMANTIC_REVIEW_ENABLED=false
```

正式演示采用“真实 Qwen 动态问答 + 证据约束模板资源”的稳定组合。`LLM_ENABLED=true` 允许全局助手和启发式追问调用真实模型；四类主训练资源默认由画像、薄弱点和本轮证据动态组装，避免整套资源连续调用模型造成长时间等待。独立语义复核默认关闭，但 ReviewAgent 的证据闭合、越界表达、难度和实操约束等确定性检查始终执行。后端已实现 OpenAI-compatible LLM 客户端、结构化输出解析和失败回退：

- `LLM_ENABLED`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT`
- `LLM_MAX_TOKENS`
- `LLM_RETRIES`
- `LLM_RESOURCE_GENERATION_ENABLED`
- `LLM_SEMANTIC_REVIEW_ENABLED`

仅当 `LLM_RESOURCE_GENERATION_ENABLED=true` 时，GenerationAgent 才调用真实模型生成整套资源；仅当 `LLM_SEMANTIC_REVIEW_ENABLED=true` 时，审核阶段才增加第二次模型语义复核。模型结果必须通过字段结构、证据 ID 闭合、实操约束和题目解析校验。调用失败、格式异常、引用越界或网络不可用时自动回退证据模板。比赛现场建议保持上述两个开关为 `false`，真实模型主要用于用户可见的动态追问。

系统同时提供 `POST /api/sessions/{session_id}/ask` 启发式追问接口。该接口不是通用聊天接口，而是将当前画像、诊断薄弱点、学习目标和最近交互送入独立子流程：材料路由、RAG 检索、启发式讲解、审核纠偏、路径决策。回答必须返回 `evidence_ids`、限制说明、后续追问、实操任务和下一动作。SQL 模式下交互写入 `learning_interactions` 表。

系统进一步提供全局上下文助手 `POST /api/assistant/ask` 与异步入口 `POST /api/assistant/tasks`。前端将当前页面、训练方向、学习者画像、学习目标、诊断摘要、可选会话 ID 和可见内容摘要作为结构化上下文传入。界面操作问题由“界面理解 Agent + 导航决策 Agent”快速处理；当前得分、薄弱点、强项、目标与方向由“上下文理解 Agent + 状态解释 Agent”基于已确认数据快速处理；领域专业问题复用材料路由、RAG 检索、启发式讲解、审核纠偏和路径决策 5 Agent 子流程。已有会话时专业回答纳入学习记录，无会话时使用临时上下文且不写入正式会话。前端支持任务停止、错误重试、清空记录和 24 小时本地续接，并展示生成模式、知识来源、证据标题和回答边界。该机制使助手能够理解用户正在看的页面和已有学习状态，同时避免采集桌面截图或屏幕外信息。

前端会区分 `llm`、`mock-template` 和 `mock-template-fallback`，只有模型实际调用并通过结构校验后才显示“真实 LLM 生成”。2026-08-11 已使用 Qwen `qwen-plus` 完成单会话端到端验证；当前仓库不包含服务密钥，比赛现场仍保留模板兜底。

## 15. 工程部署与可观测状态

`GET /api/health` 返回系统运行状态：

- `backend_status`
- `data_backend`
- `database_enabled`
- `database_connected`
- `es_enabled`
- `es_connected`
- `es_url`
- `es_index`
- `llm_enabled`
- `llm_model`
- `knowledge_source`
- `version`

前端首页会展示这些状态，便于录屏和答辩时证明系统运行在 SQL + Elasticsearch 工程模式。

## 16. 系统运行方式

推荐正式演示模式：

```env
DATABASE_ENABLED=true
DATA_BACKEND=sql
ES_ENABLED=true
LLM_ENABLED=true
LLM_RESOURCE_GENERATION_ENABLED=false
LLM_SEMANTIC_REVIEW_ENABLED=false
```

启动后端：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```powershell
cd D:\agents\frontend
npm run dev
```

初始化数据库：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.db.seed
```

导入 ES 索引：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.search.indexer
```

## 17. 数据库写入验证

完整演示后，可在 DBeaver 中查看以下表：

- `diagnosis_records`
- `agent_sessions`
- `agent_steps`
- `generated_resources`
- `learning_reports`
- `feedback_records`
- `learning_interactions`
- `async_tasks`：异步 Agent、追问和界面助手任务的进度、事件、结果及可重试请求载荷。
- `alembic_version`：数据库迁移版本。

当前已验证 MySQL 写入：

- `diagnosis_records: 2`
- `agent_sessions: 2`
- `agent_steps: 12`
- `generated_resources: 2`
- `learning_reports: 2`
- `feedback_records: 2`

## 18. ES 索引验证

可运行：

```powershell
curl.exe http://127.0.0.1:9201/_cat/indices?v
```

当前已验证：

- 索引名：`aviation_material_knowledge`
- 知识片段数量：1,766，包含人工整理基础片段、公开资料解析片段和团队实验专题切片。
- RetrievalAgent 在 ES 可用时输出检索来源：`elasticsearch`

## 19. 测试方案与当前结果

后端测试覆盖：

- 诊断评分逻辑。
- 本地 JSON 检索 fallback。
- SQL 持久化写入。
- ES 优先检索与 fallback。
- LLM 关闭时 mock 生成。
- LLM 调用失败时 mock fallback。
- Orchestrator 输出完整 6 个 Agent 步骤。
- Markdown 切片、无 BGE 时 Hybrid 到 BM25 的降级行为。
- 语料 manifest、1,766 条 chunks、来源文件、实验资产 ID 和章节或页码定位的一致性。
- 50 条测评集的数量、类别平衡、字段完整性与 ID 唯一性。

当前验证结果：

- 后端测试：`116 passed`。
- 全局上下文助手专项测评：JSON/mock 与 Elasticsearch 模式均为 39/39 通过，覆盖界面导航、学情状态、多轮指代、口语噪声、中英混合、三领域专业问答和五类安全边界；意图路由、Agent 完整性、关键内容、领域证据、安全控制与边界覆盖率均为 100%。
- 真实 Qwen 代表性质量测评：6/6 通过，真实 LLM 使用率、Elasticsearch 使用率、证据闭合率、输入理解、专业安全、画像适配和 Agent 执行得分均为 100%。审核 Agent 对 3 条越界候选执行驳回和证据模板重生，保留完整审计记录；结果仍需领域专家抽样复核。

第三批新增团队实验数据入口。模板将样品、老化工况、摩擦磨损原始值、公式计算、图像索引、损伤标注和案例结论分层保存，并通过 manifest、授权状态、SHA-256、QC 标志和双重复核控制是否允许进入 RAG。

团队数据转换采用两段式流程。`--dry-run-template` 读取模板中的演示行，重新计算滑动距离、摩擦系数、质量损失与磨损率，只在 `.tmp` 目录生成 Markdown 预览；`--ingest --index` 仅面向已审核真实数据，先生成可追溯 Markdown、登记 `source_registry.json`，再调用统一 RAG pipeline 切片并可选写入 Elasticsearch。模板预演不会污染正式语料、source registry 或 ES 索引。
- 前端构建：`npm run build` 通过。
- MySQL seed：`learners: 3`。
- ES 索引：`aviation_material_knowledge` 共 1,766 条知识片段。
- 接口闭环：诊断 -> Agent 6 步 -> ES 检索 -> 资源 -> 报告 -> 反馈，已验证通过。

第七阶段新增 50 条评测用例，位于 `evaluation/eval_cases.json`，覆盖：

- 学情诊断测试 10 条；
- 知识检索测试 10 条；
- 个性化资源生成测试 10 条；
- 审核纠偏测试 10 条；
- 反馈迭代测试 10 条。

评价指标包括检索命中率、核心知识点覆盖率、幻觉率、资源难度适配准确率、Agent 完整率和反馈决策准确率。离线结构基线入口为 `python -m app.evaluation.runner`；50 条逐条管线执行入口为 `python -m app.evaluation.full_case_runner --use-es`；审核纠偏重生入口为 `python -m app.evaluation.correction_demo_runner --use-es`。人工复核表位于 `evaluation/expert_review_form.md`。

依据比赛方案，高档专业指标目标统一为：核心知识点覆盖率 `>= 90%`、专业幻觉率 `< 5%`、画像—资源难度适配准确率 `>= 85%`。系统自动测试验证流程完整性、规则一致性和证据绑定；三项专业指标必须由领域专家逐条复核后汇总，不以关键词计数或结构检查替代。

当前可复现评测结果：

- 50 条测评用例结构完整，五类各 10 条；
- 10 条多维增强用例结构完整，15 个期望来源引用均可在来源登记中定位；
- 检索命中率 100%（10/10，Top-3 至少命中一个期望 evidence_id）；
- 三领域 Agent 完整率 100%；
- 可规则判定的反馈决策准确率 100%（8/8）；
- 50 条核心用例逐条执行通过 50/50，Agent 完整率 100%；
- 核心知识点代理覆盖率 97.27%（107/110），难度规则匹配率 96%；
- 未解决声明风险代理率 0%（0/200），反馈决策准确率 100%（10/10）；
- 8 条审核用例完成首审阻断、纠偏重生与二次审核；
- 领域专家已确认 50 条核心用例专业内容准确、信息真实可信：专业正确率 100%、核心知识点语义覆盖率 100%、幻觉率 0%、难度适配准确率 100%。复核由“项目团队领域专家组”完成，并于 2026-08-10 由项目负责人电子确认；机器代理指标继续保留用于技术审计，个人手写签名不由系统伪造。
- 新增 15 条动态追问专项用例，覆盖三领域、三类画像、工程工况问题和越权诱导。JSON fallback 与 Elasticsearch 两种模式均为 15/15 通过；工程模式 Elasticsearch 使用率、5 Agent 完整率、证据闭合率、边界覆盖率、画像适配率、决策准确率和安全控制率均为 100%。

动态追问结果记录 `generation_audit` 和独立审核审计，并随 `learning_interactions` 持久化。学情报告与 Markdown 导出包含问题、答案、检索模式、证据 ID、审核状态、下一动作和适用边界，可形成从用户输入到动态决策的完整证据链。

除核心测评集外，系统提供三组差异化学习者完整输入输出样例，位于 `evaluation/submission_examples/`。样例通过真实 REST API 生成，包含画像、诊断答案与结果、6 个 Agent 中间输出、4 类资源和学情报告，满足比赛对至少两组差异化测试数据及中间数据的要求。

自动 runner 会生成 15 条分层专家抽检清单，每类核心任务固定抽取 3 条，避免只挑选表现较好的案例。机器结果写入 `evaluation/automated_results.json`，人类可读摘要写入 `evaluation/automated_summary.md`。

## 19.1 幻觉防控、知识溯源与数据合规

系统通过以下方式降低幻觉风险：

1. RetrievalAgent 先检索 evidence_ids；
2. GenerationAgent 基于证据片段生成资源；
3. ReviewAgent 检查专业概念、依据一致性、难度匹配和实操约束；
4. 证据不足时回退 JSON/BM25，并降低输出确定性；
5. 人工专家可使用复核表抽检幻觉率。

数据合规方面，当前系统使用模拟学习者画像，不存储身份证号、手机号、学号等敏感信息。真实部署时应对学习者数据脱敏，并确保知识库资料来自公开文献、课程授权材料或已授权案例。

## 20. 当前不足与后续拓展

当前不足：

- 正式演示使用 ES BM25；Vector/Hybrid 扩展流程已实现，但尚未配置真实 BGE 模型并完成向量质量基线。
- 真实 LLM 受控调用链已经使用 Qwen `qwen-plus` 验证，资源生成、动态追问和独立审核均成功；目前样本量仍小，正式质量结论需扩大真实模型测评，Mock 继续作为现场兜底。
- 报告导出为 Markdown，尚未内置 PDF。
- 知识库规模为比赛原型级，尚未覆盖完整课程和实验数据。

后续拓展：

- 使用选定真实模型完成延迟、结构化输出成功率、证据引用有效率和专家准确性复核。
- 配置本地 BGE 后建立向量召回基线，并进一步升级 Elasticsearch `dense_vector` / kNN。
- 扩展更多航空材料方向和真实实验数据。
- 增加教师端、班级管理和长期学习轨迹分析。
- 使用 Alembic 管理数据库迁移。

## 21. 团队实验第二批证据矩阵

第二批将团队实验资料从单一案例图扩展为可用于变量控制训练的矩阵证据：

1. 紫外老化摩擦形貌专题覆盖24 h、504 h、576 h，共12项代表图像。资产记录 UVA-340、波长范围、辐照度、老化时长和图像角色；未能从源目录唯一确认的摩擦参数显式标记为待核。
2. 往复摩擦专题形成3个载荷与5个滑动距离的完整15单元矩阵。每个单元绑定接触压力、行程、频率、磨损量、硬度、样品号、光学形貌和证据 ID。
3. 系统生成1张磨损量/硬度趋势图，但不对缺失温升进行插补。温升只作为部分载荷组的辅助证据。
4. RetrievalAgent 命中新专题切片后，通过 `source_id` 和 `evidence_id` 解析对应实验资产；前端继续使用既有实验依据卡片展示图像、工况、来源和限制。
5. 第二批新增20条专项测评，覆盖紫外形貌跨时长比较、载荷/距离控制变量、定量数据与图像交叉验证、证据不足降级及反馈决策。

本批次完成后，实验资产目录共 4 个专题、53 项资产；Elasticsearch 索引共 1,766 条知识切片。在未启用 BGE 的环境中，`hybrid` 自动以 `hybrid-bm25-only` 工作，原 SQL + ES + mock LLM 闭环保持不变。



