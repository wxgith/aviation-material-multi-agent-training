# 公开实验资料增补与入库报告（2026-08-08）

> 历史快照说明：本报告记录 2026-08-08 当日的 1,685 条入库状态。当前正式验收基线已更新为 1,766 条，最新统计以 `index_manifest.json`、Elasticsearch `_count` 和 `FINAL_RELEASE.md` 为准。

## 1. 本批目标

在不改变 SQL + Elasticsearch + mock LLM 稳定闭环的前提下，补充跨领域一手实验依据，并把公开来源、解析产物、切片和前端展示串成可审计证据链。

## 2. 新增来源

| source_id | 领域 | 资料与用途 | 格式 | 新增切片 |
| --- | --- | --- | --- | ---: |
| `tire_pmc_10490132_thermal_aging` | 航空轮胎 | 天然橡胶/炭黑体系热老化、力学性能保持与交联变化 | JATS XML | 47 |
| `tire_pmc_8620932_fatigue_crack` | 航空轮胎 | 填充天然橡胶撕裂能与疲劳裂纹扩展试验 | JATS XML | 28 |
| `brake_nasa_tn_d_8006` | 航空制动 | 碳-石墨高能制动材料摩擦、磨损与剪切膜机制 | PDF | 78 |
| `composite_pmc_6865209_bvid_reconstruction` | 复合材料 | BVID 的超声 B/C 扫描与多层分层重构 | JATS XML | 78 |
| `composite_pmc_9294053_impact_dataset` | 复合材料 | CFRP 低速冲击表面形貌、深度云图和超声 C 扫描配对数据 | JATS XML | 15 |

以上开放论文采用 CC BY 4.0 版本；NASA TN D-8006 为美国政府公开技术报告。每条记录的原始 URL、许可、文件校验值和使用边界已登记在 `source_registry.json`。

## 3. 解析与切片结果

- JATS XML：由 `python -m app.rag.structured_parser` 解析，保留摘要、章节、图表说明和来源前置信息。
- NASA PDF：由 `python -m app.rag.pdf_parser` 解析 1-28 页，保留 `Page N` 定位。
- RAG 管线：按标题、段落和约 700 字符窗口切片，默认无 BGE 时以 BM25 工作。
- 本批新增：246 条切片。
- 当前总量：1,685 条，其中轮胎 795、制动 482、复合材料 408。
- 当前 ES 索引：`aviation_material_knowledge`，已同步 1,685 条。

## 4. 使用边界

1. 橡胶论文针对特定天然橡胶/炭黑配方，用于机理和试验方法训练，不能直接替代具体航空轮胎配方验证。
2. NASA TN D-8006 是历史高能制动材料试验，必须连同材料组成、载荷、速度和装置条件引用。
3. 复合材料论文中的扫描分辨率、铺层、冲击头和冲击能量属于结论适用边界。
4. 维修放行、适航限值和寿命判定仍应以当前有效的制造商手册、维修文件和适航资料为准。

## 5. 可重复命令

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.structured_parser
python -m app.rag.pdf_parser
python -m app.rag.pipeline
```

```powershell
curl.exe "http://127.0.0.1:9201/_cat/count/aviation_material_knowledge?v"
```
