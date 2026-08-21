# DBeaver 数据库查看说明

## 1. DBeaver 的作用

DBeaver 只是数据库查看和管理工具，不参与系统运行。系统运行仍由 FastAPI 后端、React 前端、SQL 数据库和 Elasticsearch 服务共同完成。

## 2. 如何连接本地 SQL 数据库

请先确认 `.env` 中的数据库连接，例如 MySQL：

```env
DATABASE_ENABLED=true
DATA_BACKEND=sql
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/agents
```

或 PostgreSQL：

```env
DATABASE_ENABLED=true
DATA_BACKEND=sql
DATABASE_URL=postgresql+psycopg://postgres:password@127.0.0.1:5432/agents
```

在 DBeaver 中新建连接：

1. 选择数据库类型：MySQL 或 PostgreSQL。
2. Host 填 `127.0.0.1`。
3. Port 按 Docker 暴露端口填写，例如 MySQL 常见为 `3306`，PostgreSQL 常见为 `5432`。
4. Database 填 `agents`，或你在本地创建的数据库名。
5. Username 和 Password 按你的 Docker 容器配置填写。
6. 点击 Test Connection，确认连接成功。

## 3. 初始化数据库表

在后端目录运行：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.db.migrate
python -m app.db.seed
```

当前版本已使用 Alembic 管理表结构，当前版本号为 `20260812_0002`。`seed` 继续保留 `create_all()` 兼容兜底，但标准初始化顺序是“先迁移、后 seed”。

## 4. 应该查看哪些表

初始化和完整演示后，重点查看：

- `learners`
- `diagnosis_records`
- `agent_sessions`
- `agent_steps`
- `generated_resources`
- `learning_reports`
- `feedback_records`
- `learning_interactions`
- `async_tasks`
- `alembic_version`

## 5. 完整演示后哪些表会新增数据

运行“加载演示案例 → 提交诊断 → Agent 流程 → 资源生成 → 学情报告 → 导出报告 → 反馈迭代”后：

- `diagnosis_records`：新增诊断得分、薄弱点、强项和诊断摘要。
- `agent_sessions`：新增一次 Agent 管线会话。
- `agent_steps`：新增 6 条 Agent 步骤记录。
- `generated_resources`：新增讲义、实操指南、分阶测试题和案例任务。
- `learning_reports`：新增 Markdown 学情报告和学习路径。
- `feedback_records`：提交反馈测试后新增反馈分数和下一步动作。
- `learning_interactions`：动态追问后新增问题、证据链、审核状态和下一动作。
- `async_tasks`：保存 Agent 管线、动态追问和界面助手的进度、事件、结果与原请求；后端重启后可恢复终态，运行中任务标记为 `interrupted` 后可重试。

## 6. 如何验证数据写入

可以在 DBeaver 中执行类似查询：

```sql
select * from diagnosis_records order by created_at desc;
select * from agent_sessions order by created_at desc;
select * from agent_steps order by created_at desc;
select * from generated_resources order by created_at desc;
select * from learning_reports order by created_at desc;
select * from feedback_records order by created_at desc;
select * from learning_interactions order by created_at desc;
select task_id, task_type, status, progress, retry_of, updated_at
from async_tasks order by updated_at desc;
select * from alembic_version;
```

如果这些表没有记录，请检查：

1. `.env` 是否设置 `DATABASE_ENABLED=true` 和 `DATA_BACKEND=sql`。
2. `DATABASE_URL` 是否与 Docker 容器端口、账号、密码一致。
3. 是否运行过 `python -m app.db.seed`。
4. 后端是否重启，使 `.env` 配置生效。

## 7. 回退 mock / JSON 模式

如需回退到无数据库模式，在 `.env` 中设置：

```env
DATABASE_ENABLED=false
DATA_BACKEND=json
```

重启后端即可。前端演示流程不受影响。
