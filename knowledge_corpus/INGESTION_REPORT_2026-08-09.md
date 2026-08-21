# FAA 2023 维修训练资料入库报告

## 1. 补充原因

项目原有航空制动与复合材料语料已包含机理研究、适航指导和实验论文，但面向机务学习者的现代检查与维护流程证据相对薄弱。本次补充 FAA 2023 年维修技术人员手册，用于建立“研究资料解释损伤机理，官方手册约束训练操作”的证据分工。

## 2. 原始资料

- 名称：FAA-H-8083-31B Aviation Maintenance Technician Handbook
- 发布机构：Federal Aviation Administration
- 年份：2023
- 官方入口：<https://www.faa.gov/regulations_policies/handbooks_manuals/aviation>
- 官方 PDF：<https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-31B_Aviation_Maintenance_Technician_Handbook.pdf>
- 本地文件：`raw_docs/FAA-H-8083-31B_Aviation_Maintenance_Technician_Handbook.pdf`
- 文件大小：111,959,636 bytes
- SHA-256：`E5ADB2696B545344B42BF7BF93C113EA94FF1456E8F8F772A6B6B02E243C4F13`

## 3. 章节选择

| 逻辑来源 ID | 领域 | PDF 物理页 | 用途 |
| --- | --- | --- | --- |
| `composite_faa_h_8083_31b_ch7_ndi` | composite | 351–355 | 目视、敲击、超声、射线与热成像检查方法及限制 |
| `brake_faa_h_8083_31b_ch13_service` | brake | 773–774、797–803 | 刹车构造、衬片/磨损指示、放气、泄漏、硬件与过热后检查 |

未将 1,053 页整本手册无差别切片。章节范围由 `pdftotext -layout` 的分页文本定位，并在解析 Markdown 中保留 `Page N`。

## 4. 处理结果

- 复材 NDI：5 个原始页，27 条切片；
- 航空刹车检查维护：9 个原始页，54 条切片；
- 本次新增：81 条切片；
- ES 索引总量：1,766 条；
- BGE：关闭；
- 实际检索策略：`hybrid-bm25-only`；
- 原 SQL + ES + mock LLM + JSON fallback 闭环保持不变。

## 5. 检索验收

运行：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.maintenance_evidence_runner
```

6 条专项用例覆盖复材敲击/超声/多方法检查与刹车衬片/放气/过热后检查。当前结果：来源 Top-5 命中率、evidence_id 可追溯率、官方来源标识率、边界说明覆盖率和 Elasticsearch 使用率均为 100%。

## 6. 使用边界

FAA 手册摘录用于教学与训练流程设计，不替代具体机型当前有效的制造商维修手册、部件维护手册、适航指令或批准维修数据。比赛提交包不重复捆绑 110 MB 原 PDF，保留来源 URL、校验值、页码 Markdown、切片和 manifest 即可。
