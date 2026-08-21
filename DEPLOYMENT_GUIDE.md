# 系统部署说明

## 1. 适用范围

本文档用于部署《面向航空工程材料损伤分析的多智能体个性化知识生成与实操训练系统》。系统由 React + Vite 前端、FastAPI 后端、MySQL、Elasticsearch、本地 JSON fallback 和可选 OpenAI-compatible LLM 组成。

推荐比赛现场使用本机 SQL + Elasticsearch 工程模式；无 Docker 或外部服务异常时，使用 JSON/mock 兜底模式。全容器部署适合评审复现与局域网试运行，不建议未经身份认证、TLS 和网络隔离直接暴露到公网。

## 2. 软件与硬件要求

- Windows 10/11 或可运行 Docker Compose 的 Linux；
- Docker Desktop 4.x 或 Docker Engine + Compose v2；
- 本机开发部署需要 Python 3.11、Node.js 20 LTS、PowerShell 5.1 以上；
- 建议内存 8 GB 以上，Elasticsearch 至少预留 2 GB；
- 建议空闲磁盘 4 GB 以上；
- 默认端口：前端 `5173`、后端 `8000`、MySQL `3306`、Elasticsearch `9201`。

## 3. 发布包安全说明

发布包不包含以下内容：

- `backend/.env` 与真实 LLM API Key；
- Python `.venv`、前端 `node_modules`、测试缓存和日志；
- MySQL、Elasticsearch 的 Docker 数据卷；
- 团队实验的 `pending_review` 原始曲线与重复压缩归档；
- 报名表中的个人信息。

部署者必须从 `.env.example` 创建自己的配置。任何曾通过聊天、截图或邮件暴露的密钥都应先撤销再重新生成。

## 4. 方式一：本机 SQL + ES 工程模式（比赛现场推荐）

### 4.1 准备基础设施

现有比赛电脑使用：

- MySQL 容器：`report-mysql`，宿主机端口 `3306`；
- Elasticsearch 容器：`agents-es`，宿主机端口 `9201`；
- MySQL 数据库：`agents`；
- ES 索引：`aviation_material_knowledge`。

先启动 Docker Desktop，等待状态变为 Running。若容器已创建：

```powershell
docker start report-mysql agents-es
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

### 4.2 安装后端

```powershell
cd D:\agents\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `backend/.env`：

```env
APP_ENV=dev
DATA_BACKEND=sql
DATABASE_ENABLED=true
DATABASE_URL=mysql+pymysql://root:<本机密码>@127.0.0.1:3306/agents

ES_ENABLED=true
ES_URL=http://127.0.0.1:9201
ES_USERNAME=
ES_PASSWORD=
ES_INDEX_KNOWLEDGE=aviation_material_knowledge

BGE_ENABLED=false
BGE_MODEL_PATH=
EMBEDDING_BACKEND=none
RETRIEVAL_MODE=hybrid

LLM_ENABLED=false
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT=60
```

### 4.3 初始化数据

首次部署或清空数据后执行：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.db.seed
python -m app.rag.pipeline
```

`seed` 创建开发演示表并导入 3 组画像；RAG pipeline 从 `knowledge_corpus/parsed_docs` 和 `chunks` 构建索引。当前冻结基线为 1,766 条 ES 文档。只在首次部署或知识库变化后重建索引。

### 4.4 安装前端

```powershell
cd D:\agents\frontend
npm ci
npm run build
```

### 4.5 一键启动

```powershell
cd D:\agents
.\scripts\start_project.ps1
```

脚本会检查 Docker、启动已有的 `report-mysql` 和 `agents-es`，再启动前后端并执行烟雾检查。

访问：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

停止本脚本启动的前后端：

```powershell
.\scripts\stop_project.ps1
```

## 5. 方式二：全 Docker Compose 部署（评审复现推荐）

此方式新建独立容器，不依赖本机 Python、Node 或原有容器名。

```powershell
cd D:\agents
Copy-Item .\deploy\.env.example .\deploy\.env
```

编辑 `deploy/.env`，至少修改 `MYSQL_ROOT_PASSWORD` 和 `MYSQL_APP_PASSWORD`。后端使用 `MYSQL_APP_USER` 专用账号访问项目库，不使用 `root`；密码会进入容器内部连接串，建议只使用字母、数字和下划线。

MySQL 官方镜像只会在首次创建空数据卷时自动建立 `MYSQL_APP_USER`。如果复用旧数据卷，应先在数据库中创建并授权应用账号，或在确认已有备份后重建数据卷。MySQL 和 Elasticsearch 的宿主机端口默认只绑定 `127.0.0.1`，避免无意暴露到局域网。

```powershell
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml up -d --build
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml ps
```

首次初始化：

```powershell
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml exec backend python -m app.db.seed
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml exec backend python -m app.rag.pipeline
```

验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
curl.exe http://127.0.0.1:9201/_cat/indices?v
```

停止但保留数据：

```powershell
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml down
```

删除容器及数据卷会清空数据库和索引，仅在确认已备份后执行：

```powershell
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml down -v
```

局域网访问时，把 `deploy/.env` 中 `PUBLIC_API_BASE` 改为部署机可访问的 IP，例如 `http://192.168.1.10:8000/api`，并把对应前端地址写入 `CORS_ORIGINS`，然后重新构建前端容器。

## 6. 方式三：JSON/mock 兜底模式

不启动 MySQL、Elasticsearch 或 LLM，编辑 `backend/.env`：

```env
DATA_BACKEND=json
DATABASE_ENABLED=false
ES_ENABLED=false
BGE_ENABLED=false
EMBEDDING_BACKEND=none
RETRIEVAL_MODE=hybrid
LLM_ENABLED=false
```

启动：

```powershell
cd D:\agents
.\scripts\start_project.ps1 -SkipDocker
```

该模式仍可完成画像、诊断、6 Agent、4 类资源、报告、导出和反馈迭代；SQL 历史记录与 ES 检索证据不可用，界面会明确显示 JSON/local fallback。

## 7. 可选真实 LLM

正式录屏建议根据网络稳定性决定是否开启。配置 OpenAI-compatible 服务：

```env
LLM_ENABLED=true
LLM_BASE_URL=https://<provider>/compatible-mode/v1
LLM_API_KEY=<仅保存在本机的密钥>
LLM_MODEL=<模型名>
LLM_TIMEOUT=60
```

调用失败、超时或输出未通过证据边界校验时，系统自动回退模板生成。禁止把 `.env`、终端密钥或带密钥截图放入提交包。

### 7.1 评委没有参赛者密钥时如何验证

评委不需要、也不应获得参赛者个人 Key。核心功能按以下两级复现：

```powershell
# 无 Docker、无数据库、无 ES、无 LLM Key：验证完整训练闭环
cd <项目目录>
.\scripts\reviewer_verify.ps1 -Mode mock

# 已启动 SQL + ES、仍无 LLM Key：验证工程连接、数据和索引
.\scripts\reviewer_verify.ps1 -Mode engineering
```

需要连同后端测试和前端构建一起执行时：

```powershell
.\scripts\reviewer_verify.ps1 -Mode all -RunRegression
```

只有在评委主动复现真实模型时才采用 BYOK：由部署者在本地注入自己的临时、限额 Key，验证后立即撤销。完整说明见 `EVALUATOR_QUICKSTART.md`。

## 8. 部署后验收

```powershell
cd D:\agents
.\scripts\run_acceptance.ps1
```

冻结基线：

- 后端 `116 passed`；
- 前端生产构建通过；
- 50/50 核心用例、15/15 动态追问、39/39 全局助手双模式通过；
- JSON/mock 完整闭环通过；
- ES 索引 1,766 条；
- MySQL 与 Elasticsearch 健康状态为 connected。

结果写入 `outputs/acceptance/acceptance_latest.json` 和 `.md`。

## 9. MySQL 验证与备份

DBeaver 连接参数：MySQL、主机 `127.0.0.1`、端口 `3306`、数据库 `agents`，账号密码以本地配置为准。完成演示后检查：

- `learners`
- `diagnosis_records`
- `agent_sessions`
- `agent_steps`
- `generated_resources`
- `learning_reports`
- `feedback_records`
- `learning_interactions`

备份示例：

```powershell
docker exec report-mysql mysqldump -uroot -p agents > agents_backup.sql
```

命令会交互式要求密码，避免把密码写入脚本。数据库备份可能包含学习过程数据，不应放入公开源码仓库；比赛数据均为模拟画像，但仍建议加密保存。

## 10. Elasticsearch 验证与恢复

```powershell
curl.exe http://127.0.0.1:9201/_cat/indices?v
curl.exe "http://127.0.0.1:9201/aviation_material_knowledge/_count"
```

ES 数据可由发布包中的切片重新构建，因此提交包不携带 ES 数据卷。索引损坏时删除目标索引后重新执行 `python -m app.rag.pipeline`。

## 11. 常见故障

| 现象 | 处理方式 |
| --- | --- |
| Docker API 无法连接 | 启动 Docker Desktop，等待 Linux Engine 为 Running |
| `report-mysql` 或 `agents-es` 不存在 | 使用 Compose 方式部署，或按本机容器配置重新创建 |
| 端口占用 | 关闭旧进程，或在脚本/Compose 环境中修改端口 |
| `database_connected=false` | 检查 MySQL 容器、数据库名、账号密码和 `DATABASE_URL` |
| `es_connected=false` | 检查 ES 容器、`ES_URL` 与宿主端口是否为 9201 |
| ES 数量不是 1,766 | 确认使用冻结知识库后重新执行 RAG pipeline |
| LLM 等待较久 | 正常范围约 30–60 秒；可停止任务或关闭 LLM 使用模板 fallback |
| 页面能开但 API 失败 | 检查 `VITE_API_BASE` 和后端 CORS 地址，前端配置变化后需重新 build |
| Compose 构建无法拉取 Python/Node/Nginx 镜像 | 检查 Docker Desktop 代理、DNS 和 Docker Hub 网络访问；网络恢复后重试 `docker compose build` |

## 12. 项目归档建议

采用 3-2-1 原则：至少 3 份副本、2 种存储介质、1 份异地或可信云存储。分别保存：

1. 脱敏提交 ZIP 和对应 SHA-256；
2. 不含密钥的源码归档；
3. 加密保存的本地 `.env` 与数据库备份；
4. 不进入提交包的原始实验归档；
5. 最终 PPT、视频、报名表和提交邮件回执。

## 13. 隔离空白环境复现

验证项目能从空白数据栈运行，同时不影响 `report-mysql` 和 `agents-es`：

```powershell
cd D:\agents
.\scripts\verify_clean_data_stack.ps1
```

脚本使用独立容器名、备用端口、随机临时密码和独立 Docker 卷，执行 MySQL seed、完整 RAG 索引、评委无密钥工程验收、三组学习者闭环、SQL 写入核对和前端生产构建，完成后自动清理。报告见 `outputs/deployment_validation/clean_data_stack_latest.md`。

Docker Hub 网络可正常拉取基础镜像时，可进一步执行全容器复现：

```powershell
.\scripts\verify_clean_deployment.ps1
```

若 `python:3.11-slim`、`node:20-alpine` 或 `nginx:1.27-alpine` 拉取超时，应保留真实失败记录，不把网络失败描述为应用构建通过。

## 14. MySQL 与 Elasticsearch 备份恢复

生成备份：

```powershell
cd D:\agents
.\scripts\backup_data.ps1
```

输出位于 `backups/aviation-training-<时间>/`，该目录被 `.gitignore` 和 `.dockerignore` 排除。备份包含 MySQL SQL dump、ES NDJSON、来源登记、索引清单、表行数、ES 文档数和 SHA-256。

在隔离空白容器中验证恢复，不覆盖现有服务：

```powershell
$latest = Get-ChildItem .\backups -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
.\scripts\verify_backup_restore.ps1 -BackupDir $latest.FullName
```

真正恢复前应先停止后端并确认目标，然后显式执行：

```powershell
.\scripts\restore_data.ps1 -BackupDir <备份目录> -Force
```

恢复会覆盖目标数据库中的同名表和目标 ES 索引。完成后重启后端并运行 `reviewer_verify.ps1 -Mode engineering`。

