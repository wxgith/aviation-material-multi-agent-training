# 三领域知识覆盖差距分析

生成时间：`2026-08-12T11:34:56.731728+00:00`

> 本报告是基于标题、标签、来源类型和证据数量的库存覆盖代理分析，不等同于专业正确率或课程完整度评价。

| 领域 | 切片 | 独立来源 | 权威来源 | 实验来源 | 团队实验 | 库存覆盖分 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 航空轮胎 | 795 | 17 | 9 | 9 | 6 | 100.0 |
| 航空刹车 | 536 | 9 | 7 | 3 | 0 | 91.2 |
| 复合材料 | 435 | 12 | 9 | 4 | 0 | 97.8 |

## 航空轮胎

| 能力维度 | 状态 | 切片 | 来源 | 代表证据 |
| --- | --- | ---: | ---: | --- |
| 材料与基础概念 | strong | 92 | 10 | tire-k01, tire-k03, tire-k07, team_tire_lyq_contact_load_temperature_evidence-c001-0ceb15e3, team_tire_lyq_contact_load_temperature_evidence-c002-f014f7c5 |
| 热氧与紫外老化 | strong | 52 | 8 | tire-k01, tire-k06, team_tire_lyq_contact_load_temperature_evidence-c006-19765927, team_tire_rxq_aging_multimodal_evidence-c001-2a1e1aa9, team_tire_rxq_aging_multimodal_evidence-c002-6b120286 |
| 摩擦磨损 | strong | 286 | 16 | tire-k02, tire-k05, tire-k06, team_tire_lyq_contact_load_temperature_evidence-c001-0ceb15e3, team_tire_lyq_contact_load_temperature_evidence-c002-f014f7c5 |
| 裂纹与剥落 | strong | 64 | 12 | tire-k03, tire-k07, team_tire_lyq_contact_load_temperature_evidence-c002-f014f7c5, team_tire_lyq_service_tire_cases-c004-87fa5212, team_tire_rxq_uv_wear_morphology-c003-12dc6f83 |
| 实验工况 | strong | 138 | 12 | tire-k02, team_tire_lyq_contact_load_temperature_evidence-c001-0ceb15e3, team_tire_lyq_contact_load_temperature_evidence-c002-f014f7c5, team_tire_lyq_contact_load_temperature_evidence-c003-163d377a, team_tire_lyq_contact_load_temperature_evidence-c004-531955f3 |
| 表征与图像 | strong | 231 | 14 | tire-k02, tire-k05, team_tire_lyq_contact_load_temperature_evidence-c007-4ed6059b, team_tire_lyq_contact_load_temperature_evidence-c008-5a35ade6, team_tire_lyq_load_distance_matrix-c001-84f52425 |
| 检查与维护判读 | strong | 558 | 13 | tire-k03, tire-k04, tire-k07, team_tire_lyq_service_tire_cases-c001-cb4082bf, team_tire_lyq_service_tire_cases-c002-83c8b834 |
| 实操训练 | strong | 97 | 11 | tire-k02, tire-k07, team_tire_lyq_contact_load_temperature_evidence-c002-f014f7c5, team_tire_lyq_load_distance_matrix-c001-84f52425, team_tire_lyq_load_distance_matrix-c002-cfaaef8c |

优先补强：
- 维持现有覆盖并做专家抽样复核

## 航空刹车

| 能力维度 | 状态 | 切片 | 来源 | 代表证据 |
| --- | --- | ---: | ---: | --- |
| 结构与基础概念 | strong | 532 | 9 | brake-k05, brake_faa_ac65_15a_landing_gear-c001-071d9116, brake_faa_ac65_15a_landing_gear-c002-4dabee9f, brake_faa_ac65_15a_landing_gear-c003-4eb13e21, brake_faa_ac65_15a_landing_gear-c004-4de41fc1 |
| 高温摩擦 | strong | 273 | 9 | brake-k01, brake-k04, brake_faa_ac65_15a_landing_gear-c005-0df984c3, brake_faa_ac65_15a_landing_gear-c006-1c383580, brake_faa_ac65_15a_landing_gear-c010-231f96c8 |
| 磨损与形貌 | strong | 436 | 9 | brake-k02, brake-k05, brake_faa_ac65_15a_landing_gear-c010-231f96c8, brake_faa_ac65_15a_landing_gear-c016-16e7a875, brake_faa_ac65_15a_landing_gear-c031-0be9fcd4 |
| 氧化与裂纹 | strong | 83 | 5 | brake-k03, brake_mdpi_aerospace_2025_predictive_wear-c118-2ea17e33, brake_nasa_cr_134989-c001-bada4d0c, brake_nasa_cr_134989-c002-5664f5db, brake_nasa_cr_134989-c003-ae2afc56 |
| 性能与热衰退 | strong | 250 | 9 | brake-k01, brake-k04, brake-k05, brake_faa_ac65_15a_landing_gear-c005-0df984c3, brake_faa_ac65_15a_landing_gear-c006-1c383580 |
| 试验工况 | missing | 0 | 0 | - |
| 检查与维护 | strong | 214 | 6 | brake_faa_ac65_15a_landing_gear-c001-071d9116, brake_faa_ac65_15a_landing_gear-c002-4dabee9f, brake_faa_ac65_15a_landing_gear-c003-4eb13e21, brake_faa_ac65_15a_landing_gear-c004-4de41fc1, brake_faa_ac65_15a_landing_gear-c005-0df984c3 |
| 失效机理 | strong | 330 | 9 | brake-k03, brake-k04, brake_faa_ac65_15a_landing_gear-c005-0df984c3, brake_faa_ac65_15a_landing_gear-c006-1c383580, brake_faa_ac65_15a_landing_gear-c013-b096659f |

优先补强：
- 补充“试验工况”的独立来源与可定位证据
- 补充授权实验记录、工况参数、图像及专家判读样例

## 复合材料

| 能力维度 | 状态 | 切片 | 来源 | 代表证据 |
| --- | --- | ---: | ---: | --- |
| 结构与基础概念 | strong | 76 | 9 | composite-k01, composite-k04, composite-k05, composite_faa_ac20_107b-c001-11e432c0, composite_faa_ac20_107b-c002-4d24664a |
| 冲击与BVID | strong | 333 | 12 | composite-k01, composite-k03, composite_damage_notes-c001-c1f9c709, composite_faa_ac20_107b-c004-1ceaa600, composite_faa_ac20_107b-c005-b0023107 |
| 分层/基体/纤维损伤 | strong | 267 | 11 | composite-k01, composite-k02, composite-k04, composite_damage_notes-c001-c1f9c709, composite_damage_notes-c002-be4cb4cb |
| 无损检测 | strong | 429 | 12 | composite-k03, composite-k05, composite_damage_notes-c003-ae26f436, composite_damage_notes-c005-d24d62ab, composite_faa_ac20_107b-c001-11e432c0 |
| 扩展与损伤容限 | strong | 201 | 12 | composite-k02, composite-k04, composite-k05, composite_damage_notes-c002-be4cb4cb, composite_damage_notes-c004-5359317b |
| 图像判读 | strong | 316 | 12 | composite-k03, composite-k05, composite_damage_notes-c003-ae26f436, composite_faa_ac20_107b-c020-a10280ff, composite_faa_ac20_107b-c021-9b1e9143 |
| 检查与维修边界 | strong | 204 | 4 | composite_faa_ac20_107b-c001-11e432c0, composite_faa_ac20_107b-c002-4d24664a, composite_faa_ac20_107b-c003-16aa3ac1, composite_faa_ac20_107b-c004-1ceaa600, composite_faa_ac20_107b-c005-b0023107 |
| 冲击试验工况 | adequate | 15 | 1 | composite_pmc_9294053_impact_dataset-c001-1a260dff, composite_pmc_9294053_impact_dataset-c002-41aec4f3, composite_pmc_9294053_impact_dataset-c003-5b7d4567, composite_pmc_9294053_impact_dataset-c004-1c4545da, composite_pmc_9294053_impact_dataset-c005-38ef5f6d |

优先补强：
- 补充授权实验记录、工况参数、图像及专家判读样例

## 待获取或待核对来源

- `tire_iso_188_2023`（tire）：Rubber, vulcanized or thermoplastic - Accelerated ageing and heat resistance tests，状态：仅登记元数据
- `tire_astm_d573`（tire）：Standard Test Method for Rubber-Deterioration in an Air Oven，状态：仅登记元数据
- `tire_astm_d5963`（tire）：Standard Test Method for Rubber Property - Abrasion Resistance，状态：仅登记元数据
- `tire_gbt_3512_2014`（tire）：硫化橡胶或热塑性橡胶 热空气加速老化和耐热试验，状态：待人工核对
- `composite_astm_d7136`（composite）：Measuring the Damage Resistance of a Fiber-Reinforced Polymer Matrix Composite to a Drop-Weight Impact Event，状态：仅登记元数据
- `composite_nasa_nde_2020`（composite）：Nondestructive Evaluation Methods and Capabilities Handbook，状态：待人工下载
- `general_faa_amt_airframe_v2`（cross_domain）：Aviation Maintenance Technician Handbook - Airframe, Volume 2，状态：待人工下载
- `composite_zenodo_4405277`（composite）：Dataset of the WP2 Cranfield: C-scan Impact Damage Data，状态：metadata_downloaded_dataset_not_bundled
