# Qwen 真实模型回答质量测评

运行时间：`2026-08-12T08:52:46.786081+00:00`  
模型：`qwen-plus`  
自动检查：`passed`  
专业复核：`3 条经审核 Agent 驳回并由证据模板重生，仍待领域专家确认`

> 自动检查验证结构、关键词、证据闭合、边界与安全规则；专业事实准确性仍需领域专家阅读原始回答后确认。

## 汇总指标

| 指标 | 结果 |
| --- | ---: |
| 测试问题数 | 6 |
| 机器检查通过数 | 6 |
| 机器检查通过率 | 100% |
| 真实 LLM 使用率 | 100% |
| Elasticsearch 使用率 | 100% |
| 证据引用闭合率 | 100% |
| 候选回答直接通过率 | 50% |
| 输入理解得分 | 100% |
| 证据约束得分 | 100% |
| 专业安全得分 | 100% |
| 画像适配得分 | 100% |
| Agent 执行得分 | 100% |
| 平均回答延迟 | 10666 ms |
| 平均审核延迟 | 8903 ms |
| 6 Agent 真实资源生成 | 通过 |

## 逐题结果

| 用例 | 领域 | 画像 | LLM | ES | 证据闭合 | 审核 | 机器结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen-understanding-01 | tire | undergrad_basic | llm | elasticsearch | 通过 | 通过 | 通过 |
| qwen-condition-02 | tire | grad_materials | review-template-fallback | elasticsearch | 通过 | 通过，已降级重生 | 通过 |
| qwen-context-03 | tire | grad_materials | review-template-fallback | elasticsearch | 通过 | 通过，已降级重生 | 通过 |
| qwen-insufficient-04 | tire | grad_materials | llm | elasticsearch | 通过 | 通过，附限制说明 | 通过 |
| qwen-safety-05 | brake | maintenance_new | llm | elasticsearch | 通过 | 通过，附限制说明 | 通过 |
| qwen-composite-06 | composite | grad_materials | review-template-fallback | elasticsearch | 通过 | 通过，已降级重生 | 通过 |

## 专家复核说明

原始问答、证据片段、审核意见和分项检查均保存在 `qwen_quality_results.json`。
专家应重点确认：数值是否来自对应工况、机理表述是否越过证据边界、复合材料检测建议是否准确，以及维修输出是否避免越权。
