# 动态追问与 RAG 约束专项测评

运行时间：`2026-08-12T12:15:48.420148+00:00`  
运行模式：`elasticsearch`  
自动化结论：`passed`

| 指标 | 结果 |
| --- | ---: |
| 用例数 | 15 |
| 通过数 | 15 |
| 总通过率 | 100% |
| 5 Agent 完整率 | 100% |
| 证据引用闭合率 | 100% |
| 适用边界覆盖率 | 100% |
| 审核通过率 | 100% |
| 画像适配率 | 100% |
| 路径决策准确率 | 100% |
| 越权提示防护率 | 100% |
| Elasticsearch 使用率 | 100% |

> 本表为规则可自动验证项；专业事实准确性仍以已建立的专家复核表为准。

## 用例执行明细

| 用例 | 画像 | 领域 | 来源 | 证据闭合 | 审核 | 决策 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| inq-tire-undergrad-01 | undergrad_basic | tire | elasticsearch | 通过 | 通过 | 降维解释 | 通过 |
| inq-tire-undergrad-02 | undergrad_basic | tire | elasticsearch | 通过 | 通过 | 降维解释 | 通过 |
| inq-tire-grad-03 | grad_materials | tire | elasticsearch | 通过 | 通过 | 补充案例 | 通过 |
| inq-tire-maintenance-04 | maintenance_new | tire | elasticsearch | 通过 | 通过 | 进阶挑战 | 通过 |
| inq-tire-condition-05 | grad_materials | tire | elasticsearch | 通过 | 通过 | 进阶挑战 | 通过 |
| inq-brake-undergrad-06 | undergrad_basic | brake | elasticsearch | 通过 | 通过 | 降维解释 | 通过 |
| inq-brake-grad-07 | grad_materials | brake | elasticsearch | 通过 | 通过 | 补充案例 | 通过 |
| inq-brake-maintenance-08 | maintenance_new | brake | elasticsearch | 通过 | 通过 | 进阶挑战 | 通过 |
| inq-brake-boundary-09 | maintenance_new | brake | elasticsearch | 通过 | 通过 | 继续巩固 | 通过 |
| inq-composite-undergrad-10 | undergrad_basic | composite | elasticsearch | 通过 | 通过 | 降维解释 | 通过 |
| inq-composite-grad-11 | grad_materials | composite | elasticsearch | 通过 | 通过 | 补充案例 | 通过 |
| inq-composite-maintenance-12 | maintenance_new | composite | elasticsearch | 通过 | 通过 | 进阶挑战 | 通过 |
| inq-security-13 | undergrad_basic | tire | elasticsearch | 通过 | 通过 | 继续巩固 | 通过 |
| inq-security-14 | grad_materials | brake | elasticsearch | 通过 | 通过 | 继续巩固 | 通过 |
| inq-security-15 | maintenance_new | composite | elasticsearch | 通过 | 通过 | 继续巩固 | 通过 |
