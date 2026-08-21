# Qwen 真实 LLM 单会话验收记录

验收日期：2026-08-11  
结果：`passed`

## 配置

- 服务：阿里云百炼 OpenAI-compatible Chat Completions
- 模型：`qwen-plus`
- 知识检索：Elasticsearch
- 数据持久化：MySQL
- 密钥：仅存于本机 `backend/.env`，本报告未记录

## 结果

| 检查项 | 结果 |
| --- | ---: |
| 最小连通性 | 通过 |
| 主流程 Agent | 6/6 |
| 个性化资源生成 | `llm` / `success` |
| 资源生成耗时 | 37,832 ms |
| 动态追问 Agent | 5/5 |
| 动态追问生成 | `llm` / `success` |
| 动态追问耗时 | 10,688 ms |
| 独立审核 | `llm-assisted-review` / `success` |
| 审核状态 | 通过，附限制说明 |
| 绑定证据 | 1 条 |
| MySQL 会话、步骤、资源、报告与追问 | 均已写入 |
| 后端回归 | 66 passed |

## 问题与修复

首次完整资源调用触发 `mock-template-fallback`，原因为 `max_tokens=1800` 截断长 JSON。按照 Qwen 结构化输出要求，JSON 请求改为 `response_format={"type":"json_object"}`，并不再发送 `max_tokens`。复测后资源生成、动态追问和独立审核均成功。

## 结论边界

这是单会话端到端连通和结构验收，不替代多领域真实模型专业质量测评。正式比赛现场仍建议保留 Mock 回退，并在录屏前确认网络、余额和模型服务状态。
