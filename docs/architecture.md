# 第二阶段系统架构

## 分层

```text
frontend/                 React + Vite 演示端
backend/app/api/          FastAPI 路由
backend/app/models/       Pydantic 数据模型
backend/app/services/     数据加载、诊断、检索、资源、报告、session
backend/app/agents/       6 个 Agent 与 orchestrator
backend/app/data/         本地 JSON 画像、题库、知识库和演示路线
```

## 闭环

1. 前端选择学习者画像、训练方向和学习目标。
2. 前端从 `/api/questions` 获取方向化诊断题。
3. `/api/diagnosis` 计算得分、水平、强项和弱项。
4. `/api/agent/run` 调度 6 个 Agent，并创建 session。
5. 前端按 session 拉取资源和报告。
6. `/api/sessions/{session_id}/feedback` 根据反馈测试正确率更新学习路径。

## Agent Pipeline

```text
DiagnosisAgent
  -> MaterialRouterAgent
  -> RetrievalAgent
  -> GenerationAgent
  -> ReviewAgent
  -> DecisionAgent
```

每个 Agent 输出 `agent_name`、`role`、`input_summary`、`output_summary`、`status`、`confidence`、`evidence_ids` 和 `details`。
