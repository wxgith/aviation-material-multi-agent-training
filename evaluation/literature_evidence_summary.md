# 公开文献实验证据专项测评

运行时间：`2026-08-12T12:15:46.189846+00:00`

| 指标 | 结果 |
| --- | ---: |
| 测评用例 | 10 |
| 文献来源 Top-5 命中率 | 100% |
| evidence_id 可追溯率 | 100% |
| 实验卡人工复核覆盖率 | 100% |
| 适用边界说明覆盖率 | 100% |
| Elasticsearch 使用率 | 100% |

自动化结论：`passed`。

人工复核确认的是文献参数转录、来源定位与适用边界，不代表项目团队重复开展了原论文试验。

## 用例明细

| 用例 | 领域 | 期望来源 | 命中 | 知识来源 |
| --- | --- | --- | --- | --- |
| lit-ret-001 | tire | tire_pmc_10490132_thermal_aging | 通过 | elasticsearch |
| lit-ret-002 | tire | tire_pmc_10490132_thermal_aging | 通过 | elasticsearch |
| lit-ret-003 | tire | tire_pmc_8620932_fatigue_crack | 通过 | elasticsearch |
| lit-ret-004 | tire | tire_pmc_8620932_fatigue_crack | 通过 | elasticsearch |
| lit-ret-005 | brake | brake_nasa_tn_d_8006 | 通过 | elasticsearch |
| lit-ret-006 | brake | brake_nasa_tn_d_8006 | 通过 | elasticsearch |
| lit-ret-007 | composite | composite_pmc_6865209_bvid_reconstruction | 通过 | elasticsearch |
| lit-ret-008 | composite | composite_pmc_6865209_bvid_reconstruction | 通过 | elasticsearch |
| lit-ret-009 | composite | composite_pmc_9294053_impact_dataset | 通过 | elasticsearch |
| lit-ret-010 | composite | composite_pmc_9294053_impact_dataset | 通过 | elasticsearch |
