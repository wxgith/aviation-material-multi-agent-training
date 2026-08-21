# 真实 LLM 接入与验收说明

## 1. 当前实现状态

系统已经实现 OpenAI-compatible `/chat/completions` 客户端，并接入两个生成环节：

1. 个性化资源生成 Agent：生成讲义、实操指南、分阶测试题和案例任务；
2. 启发式讲解 Agent：针对学习者在当前会话中提出的新问题动态生成回答；
3. 追问审核纠偏 Agent：可调用独立提示词进行二次审核。

真实模型并非系统运行的硬依赖。模型关闭、网络失败、超时、返回非 JSON、字段缺失或引用未检索 evidence_id 时，系统自动回退 mock/template，原诊断、Agent、报告和反馈闭环不中断。

## 2. 配置方式

只在本机 `D:\agents\backend\.env` 中填写配置，不要把密钥写入源码、截图或提交包：

```env
LLM_ENABLED=true
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=replace-with-local-secret
LLM_MODEL=your-model-name
LLM_TIMEOUT=60
LLM_MAX_TOKENS=1800
LLM_RETRIES=1
```

`LLM_BASE_URL` 填兼容 OpenAI Chat Completions 的版本根路径。后端会自动拼接 `/chat/completions`。本地兼容服务如不要求认证，可将 `LLM_API_KEY` 留空。

## 2.1 Qwen 实测记录

2026-08-11 使用阿里云百炼北京地域接口和 `qwen-plus` 完成真实调用验收：

- 最小连通性调用成功；
- 6 Agent 主流程完整执行，资源生成模式为 `llm`；
- 动态追问生成模式为 `llm`；
- 审核模式为 `llm-assisted-review`；
- Elasticsearch 证据已绑定，回答包含适用边界；
- MySQL 已写入 Agent 会话、6 个步骤、资源、报告和追问交互；
- 本次资源生成约 37.8 秒，动态追问约 10.7 秒；
- 后端测试 `116 passed`。

首次资源调用因设置 `max_tokens=1800` 导致长 JSON 不完整，系统按预期自动回退。随后依据 Qwen 官方结构化输出要求，JSON 请求增加 `response_format={"type":"json_object"}` 并移除输出 token 上限，复测成功。参考：[阿里云百炼结构化输出文档](https://help.aliyun.com/zh/model-studio/qwen-structured-output)。

## 3. 输出约束

模型输出必须满足：

- 资源或追问结果为可解析 JSON；
- 必填字段完整，类型正确；
- `evidence_ids` 只能引用本轮 RetrievalAgent 返回的片段；
- 实操指南包含约束条件，测试题包含解析；
- 动态回答至少给出两条适用边界；
- 审核修订稿不得引入未检索证据。

追问回答正文中的方括号证据引用也会再次校验。伪造或越界 ID 会被移除并写入 `review.invalid_text_citations`。对“忽略证据”“编造数据”“自动放行”等诱导指令，审核 Agent 会记录 `input_risk_flags`，路径决策转为“继续巩固”。

## 4. 调用审计

每次动态追问返回 `generation_audit`：

- `prompt_version`：提示词版本；
- `model`：模型名或 `mock-template`；
- `provider_configured`：服务配置是否完整；
- `latency_ms`：本次调用耗时；
- `outcome`：`success`、`fallback` 或 `disabled`；
- `fallback_reason`：回退原因，API Key 会脱敏。

审核阶段单独返回 `review.review_audit`。交互记录写入 MySQL `learning_interactions`，并进入学情报告和 Markdown 导出报告。

## 5. 最小验收步骤

1. 保持 MySQL 和 Elasticsearch 正常，配置真实模型环境变量；
2. 重启 FastAPI，检查 `/api/health` 中 `llm_enabled=true`、`llm_configured=true`；
3. 加载本科生航空轮胎案例并完成诊断；
4. 在“启发式追问”提交一个未预置问题；
5. 确认页面显示“真实 LLM 生成”，而不是模板兜底；
6. 检查生成审计的模型、提示词版本、耗时和 `outcome=success`；
7. 检查 5 Agent、Elasticsearch 证据、适用边界、审核状态和下一动作；
8. 导出报告，确认第 13 节包含本轮问题、回答和证据 ID；
9. 在 DBeaver 检查 `learning_interactions` 新增记录。

## 6. 专项质量验收

运行不依赖真实模型的动态追问基线：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.guided_inquiry_runner --use-es
```

当前规则基线为 15/15 通过，Elasticsearch 使用率、5 Agent 完整率、证据闭合率、适用边界覆盖率、画像适配率、路径决策准确率和安全控制率均为 100%。真实 Qwen 已完成 6 个代表性场景回归并全部通过机器检查，平均生成约 10.7 秒、平均审核约 8.9 秒；真实 LLM、ES、证据闭合、输入理解、专业安全、画像适配和 Agent 执行得分均为 100%。仍应继续扩充重复运行，并由领域专家抽样确认事实准确性与修订合理性。

## 7. 比赛演示建议

正式现场主线仍建议 `LLM_ENABLED=false`，用 SQL + Elasticsearch + Mock 保证稳定，并展示真实 LLM 调用、审计和失败回退代码已经完成。若已选定模型且连续预演稳定，可额外录制一段真实调用作为补充证据；现场网络不可控时不要把真实模型设为唯一可用路径。

