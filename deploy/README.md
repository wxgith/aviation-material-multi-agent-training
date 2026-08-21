# Docker Compose 部署入口

本目录提供 MySQL、Elasticsearch、FastAPI 和 React 静态前端的全容器部署配置。默认不开启真实 LLM，保留模板生成和 JSON fallback。

```powershell
cd D:\agents
Copy-Item .\deploy\.env.example .\deploy\.env
# 修改 deploy/.env 中的 MYSQL_ROOT_PASSWORD 和 MYSQL_APP_PASSWORD
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml up -d --build
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml exec backend python -m app.db.migrate
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml exec backend python -m app.db.seed
docker compose --env-file .\deploy\.env -f .\deploy\docker-compose.yml exec backend python -m app.rag.pipeline
```

后端容器启动命令已自动执行 Alembic 升级，上述显式迁移命令用于人工复核；重复执行是幂等的。

后端默认使用 `agents_app` 专用账号访问 `agents` 数据库，不使用 MySQL `root`。MySQL 与 Elasticsearch 的宿主机端口默认只绑定 `127.0.0.1`。以上账号只在首次创建数据卷时自动建立；若复用旧数据卷，请按 `DEPLOYMENT_GUIDE.md` 手工创建应用账号，或在确认已备份后重建数据卷。

访问：

- 前端：`http://127.0.0.1:5173`
- 健康检查：`http://127.0.0.1:8000/api/health`
- Elasticsearch：`http://127.0.0.1:9201/_cat/indices?v`

完整的本机部署、容器部署、初始化、验收、备份和故障排查说明见根目录 `DEPLOYMENT_GUIDE.md`。
