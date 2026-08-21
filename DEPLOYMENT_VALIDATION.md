# 部署与发布包验证记录

验证日期：2026-08-12

## 验证结果

| 项目 | 结果 |
| --- | --- |
| Docker Compose 配置解析 | 通过，`docker compose config --quiet` 返回成功 |
| 候选 ZIP 逐文件 SHA-256 | 已有候选包通过；新增本轮材料后以最新 `PACKAGE_MANIFEST.json` 为准 |
| 发布包密钥与禁止目录检查 | 通过，未包含 `.env`、API Key、`.venv`、`node_modules`、日志或 `pending_review` |
| 发布包后端测试 | 116 passed |
| 发布包前端干净安装 | `npm ci` 通过，67 个包，0 vulnerabilities |
| 发布包前端生产构建 | 通过 |
| 三组完整输入输出样例 | 已用 1.2.0 当前后端和 `LLM_ENABLED=false` 重新生成 |
| Compose 镜像完整构建 | 未完成：当前网络无法从 Docker Hub 拉取 Python、Node、Nginx 基础镜像 |
| 独立空白 MySQL/ES 数据栈 | 通过：seed 3 画像、ES 1,766 条、3 组闭环、18 Agent 步骤、前端构建通过 |
| MySQL + ES 备份 | 通过：原生 SQL dump、ES NDJSON、SHA-256 和表行数清单 |
| 隔离恢复验证 | 通过：8 张 SQL 表逐表核对，ES 1,766 条核对，源服务未修改 |

## Compose 构建边界

构建命令已经进入 Docker BuildKit，Dockerfile 与 Compose 服务定义可被正确读取；失败发生在请求 Docker Hub 匿名令牌阶段，不是 Dockerfile 语法、项目依赖或前端构建错误。网络、代理或 DNS 恢复后执行：

```powershell
cd D:\agents
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml build backend frontend
```

随后按 `DEPLOYMENT_GUIDE.md` 启动、seed 并构建 ES 索引。

## 当前候选包

最新候选包应在本轮回归结束后重新生成，文件名与 SHA-256 以 `release_packages/` 下最新产物为准。

该包用于团队复核，不是最终提交包，因为尚未包含正式 MP4 演示视频和报名表。加入人工材料后必须重新运行：

```powershell
.\scripts\build_release_package.ps1 -Final -PackageName "学校—申报人姓名—作品名称—联系电话"
```

