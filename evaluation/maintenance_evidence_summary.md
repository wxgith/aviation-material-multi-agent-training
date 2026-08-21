# FAA 维修训练证据专项测评

运行时间：`2026-08-12T12:15:46.759841+00:00`

| 指标 | 结果 |
| --- | ---: |
| 测评用例 | 6 |
| 官方来源 Top-5 命中率 | 100% |
| evidence_id 可追溯率 | 100% |
| 官方来源标识率 | 100% |
| 使用边界说明覆盖率 | 100% |
| Elasticsearch 使用率 | 100% |

自动化结论：`passed`。

这些资料用于训练检查思路，不能替代具体机型的现行制造商手册、维修方案或批准数据。

## 用例明细

| 用例 | 领域 | 期望来源 | 命中 | 知识来源 |
| --- | --- | --- | --- | --- |
| maint-ret-001 | composite | composite_faa_h_8083_31b_ch7_ndi | 通过 | elasticsearch |
| maint-ret-002 | composite | composite_faa_h_8083_31b_ch7_ndi | 通过 | elasticsearch |
| maint-ret-003 | composite | composite_faa_h_8083_31b_ch7_ndi | 通过 | elasticsearch |
| maint-ret-004 | brake | brake_faa_h_8083_31b_ch13_service | 通过 | elasticsearch |
| maint-ret-005 | brake | brake_faa_h_8083_31b_ch13_service | 通过 | elasticsearch |
| maint-ret-006 | brake | brake_faa_h_8083_31b_ch13_service | 通过 | elasticsearch |
