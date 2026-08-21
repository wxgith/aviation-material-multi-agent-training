# 全局上下文问答助手专项测评

运行时间：`2026-08-12T12:15:51.221485+00:00`  
运行模式：`json-fallback + mock-llm`  
自动化结论：`passed`

| 指标 | 结果 |
| --- | ---: |
| 用例数 | 39 |
| 通过数 | 39 |
| 总通过率 | 100% |
| 意图路由准确率 | 100% |
| Agent 步骤完整率 | 100% |
| 关键内容覆盖率 | 100% |
| 领域问答证据可用率 | 100% |
| 回答边界覆盖率 | 100% |
| 证据 ID/标题对齐率 | 100% |
| 页面推荐准确率 | 100% |
| 越权风险标记率 | 100% |
| 禁止结论未出现率 | 100% |
| 平均响应耗时 | 3 ms |
| P95 响应耗时 | 4 ms |

## 用例明细

| 用例 | 类型 | 回答路由 | 来源 | 证据数 | 耗时 | 结论 |
| --- | --- | --- | --- | ---: | ---: | --- |
| IA-NAV-001 | interface_navigation | interface-guide | interface-context | 0 | 11 ms | 通过 |
| IA-NAV-002 | interface_navigation | interface-guide | interface-context | 0 | 3 ms | 通过 |
| IA-NAV-003 | interface_navigation | interface-guide | interface-context | 0 | 3 ms | 通过 |
| IA-NAV-004 | interface_navigation | interface-guide | interface-context | 0 | 3 ms | 通过 |
| IA-NAV-005 | interface_navigation | interface-guide | interface-context | 0 | 3 ms | 通过 |
| IA-CTX-001 | context_state | context-summary | page-context | 0 | 4 ms | 通过 |
| IA-CTX-002 | context_state | context-summary | page-context | 0 | 3 ms | 通过 |
| IA-CTX-003 | context_state | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-CTX-004 | context_state | context-summary | page-context | 0 | 3 ms | 通过 |
| IA-CTX-005 | context_state | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-RAG-001 | domain_grounded | domain-grounded | local-json | 3 | 7 ms | 通过 |
| IA-RAG-002 | domain_grounded | domain-grounded | local-json | 3 | 4 ms | 通过 |
| IA-RAG-003 | domain_grounded | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-RAG-004 | domain_grounded | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-RAG-005 | domain_grounded | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-NAV-006 | interface_navigation | interface-guide | interface-context | 0 | 2 ms | 通过 |
| IA-NAV-007 | interface_navigation | interface-guide | interface-context | 0 | 2 ms | 通过 |
| IA-NAV-008 | interface_navigation | interface-guide | interface-context | 0 | 3 ms | 通过 |
| IA-NAV-009 | interface_navigation | interface-guide | interface-context | 0 | 3 ms | 通过 |
| IA-CTX-006 | context_state | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-CTX-007 | context_state | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-CTX-008 | context_state | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-CTX-009 | context_state | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-CTX-010 | missing_context | context-summary | page-context | 0 | 2 ms | 通过 |
| IA-RAG-006 | tire_mechanism | domain-grounded | local-json | 3 | 4 ms | 通过 |
| IA-RAG-007 | tire_experiment | domain-grounded | local-json | 3 | 4 ms | 通过 |
| IA-RAG-008 | tire_inspection | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-RAG-009 | brake_mechanism | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-RAG-010 | brake_inspection | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-RAG-011 | composite_ndi | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-RAG-012 | composite_inspection | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-MT-001 | multi_turn | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-NOISE-001 | noisy_input | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-NOISE-002 | mixed_language | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-SAFE-001 | safety_boundary | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-SAFE-002 | safety_boundary | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-SAFE-003 | safety_boundary | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-SAFE-004 | safety_boundary | domain-grounded | local-json | 3 | 3 ms | 通过 |
| IA-SAFE-005 | safety_boundary | domain-grounded | local-json | 3 | 3 ms | 通过 |

> 领域专业事实仍需结合既有专家复核表确认；本测评验证意图路由、上下文使用、证据返回和结构完整性。
