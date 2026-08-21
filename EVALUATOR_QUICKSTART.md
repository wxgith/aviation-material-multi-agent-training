# 评委无密钥复现与验收指南

## 1. 密钥原则

评委不会、也不应获得参赛者个人的模型 API Key。发布包主动排除 `backend/.env`、`deploy/.env` 和任何形如 `sk-...` 的密钥；模型密钥不是作品源代码或测试数据的一部分。

本系统采用三层可验证设计：

| 验证层级 | 依赖 | 可验证内容 | 是否需要 LLM Key |
| --- | --- | --- | --- |
| JSON/mock 闭环 | Python 依赖 | 画像、诊断、6 Agent、4 类资源、报告、导出、反馈迭代 | 否 |
| SQL + ES 工程模式 | MySQL、Elasticsearch | 上述闭环、SQL 持久化、ES 检索、证据 ID、系统健康状态 | 否 |
| 可选真实 LLM | OpenAI-compatible 服务 | 动态生成、结构化校验、审核驳回和模板回退 | 是，由部署者自行提供 |

因此，比赛要求中的核心闭环、Agent 调度、RAG 证据链和工程持久化均可在无个人密钥条件下复现。真实模型只是一条可选增强路径，不是系统可运行性的单点依赖。

## 2. 最快验收：无 Docker、无密钥

安装后端依赖后执行：

```powershell
cd <解压后的项目目录>
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
.\scripts\reviewer_verify.ps1 -Mode mock
```

脚本在 FastAPI 进程内临时关闭 SQL、Elasticsearch、BGE 和 LLM，不读取模型密钥，也不向外部数据库写入数据。通过标准包括：

- 本地 JSON 画像和题库加载成功；
- 诊断完成；
- 6 个 Agent 按顺序执行；
- 讲义、实操指南、分阶测试题和案例任务生成；
- 学情报告与 Markdown 导出完成；
- 反馈触发 4 步动态迭代。

报告输出到：

```text
outputs/reviewer_verification/reviewer_verification_latest.json
outputs/reviewer_verification/reviewer_verification_latest.md
```

## 3. 工程模式验收：SQL + Elasticsearch，无密钥

按 `DEPLOYMENT_GUIDE.md` 启动 MySQL、Elasticsearch、后端和前端，将 `LLM_ENABLED=false`，然后执行：

```powershell
cd <项目目录>
.\scripts\reviewer_verify.ps1 -Mode engineering
```

脚本核验：

- `/api/health` 返回后端正常；
- MySQL 已连接；
- Elasticsearch 已连接并被选为知识来源；
- ES 知识索引存在且文档数大于 0；
- 至少 3 组画像、3 个训练方向和 5 道轮胎诊断题可读取；
- LLM 失败回退能力处于可用状态。

随后可在网页执行“加载演示案例 -> 提交诊断 -> Agent 流程 -> 资源 -> 报告 -> 导出 -> 反馈”，并在 DBeaver 查看新增的诊断、会话、Agent 步骤、资源、报告和反馈记录。

运行完整代码回归：

```powershell
.\scripts\reviewer_verify.ps1 -Mode all -RunRegression
```

## 4. 可选真实 LLM 验收（BYOK）

如评审确需复现真实模型调用，应采用 BYOK（Bring Your Own Key）方式：评委使用自己的兼容服务密钥，或参赛团队在现场临时注入一枚限额、限时密钥。密钥仅写入本机未提交的 `backend/.env` 或部署环境变量：

```env
LLM_ENABLED=true
LLM_BASE_URL=https://<provider>/compatible-mode/v1
LLM_API_KEY=<部署者自己的临时密钥>
LLM_MODEL=<模型名>
```

验证时观察 `/api/health` 的 `llm.mode`、页面的生成模式和单次回答的 `generation_audit`。只有远端调用及结构校验均成功时，页面才标记为真实 LLM；超时、服务错误或证据边界不合格会自动回退模板生成。

项目已保留真实 Qwen 代表性回归结果，位于 `evaluation/qwen_quality_results.json` 和 `evaluation/qwen_interface_assistant_results.json`。这些文件证明接口链路曾成功运行，但不替代评委用自有 Key 的独立复现。

## 5. 安全注意事项

1. 不在源码、PPT、视频、截图、终端历史或提交邮件中展示密钥。
2. 曾在聊天、截图或邮件中出现过的密钥必须撤销并重新生成。
3. 临时验证密钥应设置额度、有效期和来源限制，验证结束后立即撤销。
4. 公开或交给评委的服务不应使用 MySQL `root` 账号。
5. 对外部署前还需增加身份认证、TLS、访问限流和网络隔离；当前 Compose 配置定位为本地/局域网评审复现。

## 6. 结果判读

评委无需相信预录视频或静态截图：可以直接运行无密钥闭环、检查 6 Agent 返回结构、查询 ES 证据 ID、查看 MySQL 新增记录，并核对发布包 `PACKAGE_MANIFEST.json` 中的 SHA-256。真实 LLM 能力作为可选附加验证，不影响核心功能验收。
