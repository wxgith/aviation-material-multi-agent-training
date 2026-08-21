# 项目操作脚本

## 一键启动

先打开 Docker Desktop，再在 PowerShell 执行：

```powershell
cd D:\agents
.\scripts\start_project.ps1
```

脚本会检查并启动 `report-mysql`、`agents-es`，验证后端是否包含当前异步任务接口，再分别打开后端和前端终端。服务就绪后会执行画像、领域、数据库、ES 和任务 API 冒烟检查，并打开系统页面。只有与当前版本兼容的已有服务才会被复用。

常用参数：

```powershell
# 只启动并检查，不自动打开浏览器
.\scripts\start_project.ps1 -NoBrowser

# 后台启动，适合录屏前预热
.\scripts\start_project.ps1 -Headless -NoBrowser

# Docker 已由其他方式管理时跳过容器启动
.\scripts\start_project.ps1 -SkipDocker
```

查看当前状态：

```powershell
.\scripts\project_status.ps1
```

停止由一键脚本创建的前后端进程，不停止 Docker：

```powershell
.\scripts\stop_project.ps1
```

如需同时停止两个项目容器，使用 `.\scripts\stop_project.ps1 -StopDocker`。手工启动的终端不会被停止脚本误杀。

## 环境检查

```powershell
.\scripts\check_environment.ps1
```

该命令只检查运行环境，不修改数据库和 Elasticsearch 索引。

## 最终自动验收

先保证后端和前端已经启动，再执行：

```powershell
.\scripts\run_acceptance.ps1
```

完整验收会实时显示每个子命令的输出，并在 `outputs/acceptance/logs/` 保存独立的 stdout、stderr 和退出码日志。默认普通步骤超时为 900 秒，第 3 步离线确定性评测超时为 120 秒；没有新输出时每 15 秒打印一次心跳，避免误认为脚本失去响应。

若只需复现第 3 步，不检查 API、MySQL、Elasticsearch，也不执行其余 13 步：

```powershell
.\scripts\run_acceptance.ps1 -OnlyStep 3
```

该模式强制使用 JSON、本地检索、mock 生成，逐条显示 `START` / `DONE`。其中 50 条是测评数据结构校验；随后实际执行 10 条检索、3 个领域的 6 Agent 样例及 10 条反馈决策。全部 50 条通过 6 Agent 的执行位于完整验收第 4 步。

自定义超时和心跳间隔：

```powershell
.\scripts\run_acceptance.ps1 -OnlyStep 3 -Step3TimeoutSeconds 120 -HeartbeatSeconds 10
.\scripts\run_acceptance.ps1 -CommandTimeoutSeconds 1200 -HeartbeatSeconds 15
```

发生超时时，错误会直接打印最后一条 `START`；若它后面没有对应的 `DONE`，该行就是优先排查的阶段和 case。完整排查方法见 `docs/验收卡顿排查说明.md`。

验收内容包括：

- SQL、Elasticsearch 和 API 健康状态；
- ES 索引文档数量；
- 核心 50 条自动测评；
- 第二批 20 条实验依据测评；
- 10 条公开文献证据专项回归；
- JSON/mock 模式完整 API 闭环；
- 后端全量 `pytest`；
- 前端生产构建。

报告会写入：

```text
outputs/acceptance/acceptance_latest.json
outputs/acceptance/acceptance_latest.md
submission_materials/07_接口测试与单元测试/最终自动验收报告.json
submission_materials/07_接口测试与单元测试/最终自动验收报告.md
```

该命令不会执行 seed，也不会重建 ES 索引。

只运行兜底模式闭环：

```powershell
.\scripts\run_fallback_acceptance.ps1
```

该命令会在 FastAPI 进程内临时关闭 SQL、ES、LLM 和 BGE，验证诊断、6 Agent、四类资源、报告导出和反馈迭代，不会停止当前 Docker 容器。

## 评委无密钥验收

只验证不依赖外部服务的完整闭环：

```powershell
.\scripts\reviewer_verify.ps1 -Mode mock
```

后端已启动 SQL + ES 工程模式时，验证健康状态、画像、题库和 ES 索引：

```powershell
.\scripts\reviewer_verify.ps1 -Mode engineering
```

同时执行两种模式、后端全量测试和前端生产构建：

```powershell
.\scripts\reviewer_verify.ps1 -Mode all -RunRegression
```

该脚本从不要求或打印 LLM API Key，结果写入 `outputs/reviewer_verification/`。评委复现说明见根目录 `EVALUATOR_QUICKSTART.md`。

## 隔离空白环境复现

```powershell
.\scripts\verify_clean_data_stack.ps1
```

脚本复用本机已有 MySQL/ES 镜像，创建独立容器、端口、账号和数据卷，从空库完成 seed、1,766 条索引、三组完整闭环、SQL 写入和前端构建，之后自动清理，不修改日常演示数据。

Docker Hub 网络正常时可进一步运行全容器验证：

```powershell
.\scripts\verify_clean_deployment.ps1
```

## 数据备份与恢复

```powershell
.\scripts\backup_data.ps1
$latest = Get-ChildItem .\backups -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
.\scripts\verify_backup_restore.ps1 -BackupDir $latest.FullName
```

真正恢复现有服务必须显式执行 `restore_data.ps1 -Force`；默认调用会拒绝覆盖。

## 提交包完整性清单

在最终加入报名表、演示视频和签字材料后执行：

```powershell
.\scripts\generate_submission_manifest.ps1
.\scripts\verify_submission_manifest.ps1
```

生成的 `submission_materials/SUBMISSION_MANIFEST.json` 保存每个提交文件的 SHA-256，可用于压缩前后核对文件是否遗漏或损坏。

## 构建脱敏发布包

生成不含 `.env`、API Key、虚拟环境、`node_modules`、日志和原始 `pending_review` 数据的候选 ZIP：

```powershell
cd D:\agents
.\scripts\build_release_package.ps1
```

加入正式视频和报名表后生成最终包：

```powershell
.\scripts\build_release_package.ps1 -Final
```

校验目录或 ZIP 中的逐文件 SHA-256：

```powershell
.\scripts\verify_release_package.ps1 -PackagePath <ZIP路径>
```
