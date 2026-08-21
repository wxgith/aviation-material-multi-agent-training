# 发布包阅读入口

本发布包是比赛作品的脱敏可部署候选版本，包含：

- `backend/`：FastAPI 源码、依赖和 107 项测试；
- `frontend/`：React + Vite 源码及生产构建产物；
- `knowledge_corpus/`：可复现切片、来源清单、实验资产与脱敏团队数据；
- `evaluation/`：50 条主测评、专项测评与执行结果；
- `submission_materials/`：设计方案、PPT 候选、讲稿、测试数据和验收材料；
- `deploy/`：全容器部署配置；
- `scripts/`：启动、停止、验收、打包和校验脚本。

## 首次阅读顺序

1. `FINAL_FUNCTIONAL_AUDIT.md`：当前功能状态和最终验收结论；
2. `EVALUATOR_QUICKSTART.md`：无个人密钥的评委复现路径；
3. `DEPLOYMENT_GUIDE.md`：本机或 Docker Compose 部署；
4. `README.md`：系统功能、架构和比赛要求对应关系；
5. `submission_materials/提交包说明.md`：比赛材料位置和人工待办；
6. `PACKAGE_MANIFEST.md`：发布包文件数量、大小和 SHA-256 校验说明。

## 安全说明

发布包不包含任何 `.env`、真实 API Key、Python 虚拟环境、`node_modules`、Docker 数据卷、日志或临时文件。核心闭环和 SQL + ES 验收均不需要模型密钥；可选真实 LLM 验证由部署者采用 BYOK 在本地临时配置。

当前包仍是提交候选包。正式提交前必须补入 10 分钟以内演示视频、报名表、团队身份信息，并最终确认 PPT 和设计方案封面。

