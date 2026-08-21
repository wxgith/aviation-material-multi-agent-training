---
source_id: team_tire_lyq_load_distance_matrix
domain: tire
source_authority: team_authorized_experiment
authorization_status: authorized
review_status: reviewed
---

# 不同载荷往复摩擦的载荷-距离-形貌训练矩阵

本专题绑定圆柱-平面往复摩擦的 3 个载荷、5 个滑动距离、15 个定量记录与代表性光学形貌。试验行程 10 mm、频率 3.3 Hz。温升资料目前只能作为部分载荷组的辅助证据，不能插补为 15 个单元的温升矩阵。

## 十五个工况单元

| 载荷 | 接触压力 | 距离 | 磨损量 | 硬度 | 图像资产 | 证据 ID |
| --- | --- | --- | --- | --- | --- | --- |
| 40 N | 1.2 MPa | 20 m | 0.0125 g | 65.2750 HA | `LYQ-LOAD-L40-D020-OPT-01` | `LYQ-LOAD-P1.2-D020` |
| 50 N | 1.5 MPa | 20 m | 0.0180 g | 60.6286 HA | `LYQ-LOAD-L50-D020-OPT-01` | `LYQ-LOAD-P1.5-D020` |
| 60 N | 1.8 MPa | 20 m | 0.0365 g | 58.8857 HA | `LYQ-LOAD-L60-D020-OPT-01` | `LYQ-LOAD-P1.8-D020` |
| 40 N | 1.2 MPa | 40 m | 0.0155 g | 63.9286 HA | `LYQ-LOAD-L40-D040-OPT-01` | `LYQ-LOAD-P1.2-D040` |
| 50 N | 1.5 MPa | 40 m | 0.0295 g | 58.9000 HA | `LYQ-LOAD-L50-D040-OPT-01` | `LYQ-LOAD-P1.5-D040` |
| 60 N | 1.8 MPa | 40 m | 0.0685 g | 57.6857 HA | `LYQ-LOAD-L60-D040-OPT-01` | `LYQ-LOAD-P1.8-D040` |
| 40 N | 1.2 MPa | 80 m | 0.0370 g | 60.5667 HA | `LYQ-LOAD-L40-D080-OPT-01` | `LYQ-LOAD-P1.2-D080` |
| 50 N | 1.5 MPa | 80 m | 0.0505 g | 55.1429 HA | `LYQ-LOAD-L50-D080-OPT-01` | `LYQ-LOAD-P1.5-D080` |
| 60 N | 1.8 MPa | 80 m | 0.1025 g | 53.1143 HA | `LYQ-LOAD-L60-D080-OPT-01` | `LYQ-LOAD-P1.8-D080` |
| 40 N | 1.2 MPa | 120 m | 0.0445 g | 56.3714 HA | `LYQ-LOAD-L40-D120-OPT-01` | `LYQ-LOAD-P1.2-D120` |
| 50 N | 1.5 MPa | 120 m | 0.0890 g | 53.3833 HA | `LYQ-LOAD-L50-D120-OPT-01` | `LYQ-LOAD-P1.5-D120` |
| 60 N | 1.8 MPa | 120 m | 0.1390 g | 49.7500 HA | `LYQ-LOAD-L60-D120-OPT-01` | `LYQ-LOAD-P1.8-D120` |
| 40 N | 1.2 MPa | 160 m | 0.0600 g | 52.5571 HA | `LYQ-LOAD-L40-D160-OPT-01` | `LYQ-LOAD-P1.2-D160` |
| 50 N | 1.5 MPa | 160 m | 0.1205 g | 51.2286 HA | `LYQ-LOAD-L50-D160-OPT-01` | `LYQ-LOAD-P1.5-D160` |
| 60 N | 1.8 MPa | 160 m | 0.1605 g | 46.5714 HA | `LYQ-LOAD-L60-D160-OPT-01` | `LYQ-LOAD-P1.8-D160` |

## 训练与审核边界

- 同载荷比较距离效应，同距离比较载荷效应，避免混合变量后直接归因。
- 形貌观察必须与磨损量和硬度记录交叉验证，代表图不能替代重复试验统计。
- 温升证据状态应显式显示为 partial；没有单元记录时不得生成温度数值。
- 所有趋势只适用于已测载荷、接触形式、距离和环境范围。
