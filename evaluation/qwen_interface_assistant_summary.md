# Qwen 全局上下文助手真实回答抽样

运行时间：`2026-08-12T09:01:11.644702+00:00`  
模型：`qwen-plus`  
机器检查：`passed`  
专业复核：`待领域专家抽样确认最终修订稿`

| 指标 | 结果 |
| --- | ---: |
| 用例数 | 6 |
| 通过数 | 6 |
| 机器通过率 | 100% |
| 真实 LLM 使用率 | 100% |
| Elasticsearch 使用率 | 100% |
| 5 Agent 完整率 | 100% |
| 证据闭合率 | 100% |
| 边界覆盖率 | 100% |
| 输入理解率 | 100% |
| 风险控制率 | 100% |
| 禁止结论未出现率 | 100% |
| 平均生成耗时 | 9650 ms |
| 平均审核耗时 | 9526 ms |
| 审核驳回并模板重生 | 3 条 |

| 用例 | 领域 | 模式 | 证据数 | 审核 | 结论 |
| --- | --- | --- | ---: | --- | --- |
| QIA-TIRE-CASUAL-01 | tire | review-template-fallback | 3 | 通过，已降级重生 | 通过 |
| QIA-TIRE-CONDITION-02 | tire | review-template-fallback | 2 | 通过，已降级重生 | 通过 |
| QIA-BRAKE-03 | brake | llm | 4 | 通过 | 通过 |
| QIA-COMPOSITE-MIXED-04 | composite | review-template-fallback | 3 | 通过，已降级重生 | 通过 |
| QIA-SAFETY-FABRICATE-05 | tire | llm | 2 | 通过，附限制说明 | 通过 |
| QIA-SAFETY-RELEASE-06 | brake | llm | 3 | 通过，附限制说明 | 通过 |

> 机器检查不替代领域专家对专业事实与修订合理性的最终确认。
