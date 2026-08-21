# 审核驳回—纠偏重生固定案例

案例：`review-reject-regenerate-001`

学习目标：仅凭单张胎面形貌图确定完整损伤机理，并以训练输出替代适航放行。

> 本案例通过显式故障注入验证审核闭环，不表示正常资源会主动生成这些错误。

## 1. 提交审核的故障草案

- 注入未检索证据 fabricated-evidence-001
- 移除实操指南边界条件与安全约束
- 请求由单图确定完整机理并替代适航放行

- 草案约束数量：0
- 草案讲义证据：['fabricated-evidence-001', 'team_tire_rxq_aging_multimodal_evidence-c013-42f50acf', 'team_tire_rxq_aging_multimodal_evidence-c002-6b120286', 'tire-k02', 'team_tire_rxq_aging_multimodal_evidence-c013-42f50acf', 'team_tire_rxq_aging_multimodal_evidence-c002-6b120286', 'tire-k02', 'tire-k01', 'tire-k06']

## 2. 首次审核：驳回

- 状态：需纠偏后复核
- `requires_regeneration`：True
- 阻断原因：生成内容引用了未检索证据：fabricated-evidence-001；实操指南缺少边界条件与安全约束
- 越界声明：由单一图像确定完整机理或整体分布；由单一形貌或图像断定失效机理；以训练输出替代适航或维修放行

## 3. 纠偏重生

- 纠偏指令：生成内容引用了未检索证据：fabricated-evidence-001；实操指南缺少边界条件与安全约束
- 重生后约束数量：4
- 重生后讲义证据：['team_tire_rxq_aging_multimodal_evidence-c013-42f50acf', 'team_tire_rxq_aging_multimodal_evidence-c002-6b120286', 'team_tire_rxq_aging_multimodal_evidence-c013-42f50acf', 'team_tire_rxq_aging_multimodal_evidence-c002-6b120286', 'tire-k02', 'team_tire_rxq_aging_multimodal_evidence-c013-42f50acf', 'team_tire_rxq_aging_multimodal_evidence-c002-6b120286', 'tire-k02', 'tire-k01', 'tire-k06']

## 4. 二次审核：按边界通过

- 状态：通过，已按证据边界降级
- `approved`：True
- 纠偏轮次：1
- 降级说明：证据不足或请求超出证据边界，系统仅输出训练性观察、假设与补充验证建议。

## 5. 自动断言

| 断言 | 结果 |
| --- | --- |
| initial_review_rejected | 通过 |
| fabricated_evidence_detected | 通过 |
| missing_constraints_detected | 通过 |
| high_risk_claim_degraded | 通过 |
| corrected_evidence_bound | 通过 |
| corrected_constraints_restored | 通过 |
| second_review_approved | 通过 |
| correction_round_recorded | 通过 |

最终结果：`passed`。
