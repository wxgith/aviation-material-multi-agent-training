# 多智能体审核门对比实验

> 本报告由归档的真实 Qwen 输出与确定性测评结果离线计算，不重新调用模型或数据库。

## 1. 实验问题

在检索证据和学习者画像相同的条件下，比较：

- A 组：RAG + Qwen 原始候选，不经过 ReviewAgent 质量门。
- B 组：RAG + Qwen + ReviewAgent；不合格候选驳回并使用证据模板重生。

## 2. 配对结果

| 指标 | 结果 |
| --- | ---: |
| 真实 Qwen 配对样本 | 6 |
| 原始候选直接通过审核 | 3/6 (50%) |
| ReviewAgent 实际介入 | 3/6 (50%) |
| 审核与重生后机器检查通过 | 6/6 (100%) |
| 机器验收通过率变化 | +50 个百分点 |
| 证据闭合 | 6/6 |
| 审核记录的风险项 | 21 |

## 3. 逐例状态

| 用例 | 领域 | 画像 | 原始候选 | 审核介入 | 风险项 | 最终模式 | 最终机器检查 |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| qwen-understanding-01 | tire | undergrad_basic | 通过 | 否 | 0 | llm | 通过 |
| qwen-condition-02 | tire | grad_materials | 驳回 | 是 | 6 | review-template-fallback | 通过 |
| qwen-context-03 | tire | grad_materials | 驳回 | 是 | 6 | review-template-fallback | 通过 |
| qwen-insufficient-04 | tire | grad_materials | 通过 | 否 | 1 | llm | 通过 |
| qwen-safety-05 | brake | maintenance_new | 通过 | 否 | 1 | llm | 通过 |
| qwen-composite-06 | composite | grad_materials | 驳回 | 是 | 7 | review-template-fallback | 通过 |

## 4. 50 条完整管线补充结果

| 指标 | 结果 |
| --- | ---: |
| 完整执行 | 50/50 |
| 6 Agent 完整率 | 100% |
| 触发纠偏的用例 | 8 |
| 核心知识点代理覆盖率 | 97.27% |
| 难度规则匹配率 | 96% |
| 审核后未解决断言风险代理率 | 0% |

## 5. 可引用结论

在 6 条真实 Qwen 代表性场景中，未经审核的 RAG + Qwen 候选仅 3/6 直接通过；ReviewAgent 对另 3 条执行驳回和证据模板重生，最终 6/6 通过机器检查。该结果说明多智能体审核门不是界面展示，而会实际改变不合格模型输出。

## 6. 结论边界

- 该实验衡量审核门的风险拦截和结构化验收作用，不直接等价于学习效果提升。
- 配对样本为 6 条真实 Qwen 代表性场景，样本量有限，仍需外部专家盲审。
- 候选答案均已使用 RAG 证据；本实验不宣称完成了无 RAG 单模型对照。
- 50 条完整管线结果用于补充工程稳定性，不与 6 条 Qwen 样本合并计算同一比例。
