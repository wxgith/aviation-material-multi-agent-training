# 第二批公开资料入库报告

## 1. 入库范围

本批资料用于补强航空轮胎、航空碳/碳刹车和复合材料冲击损伤三个方向。选择标准为：来源可核验、正文或元数据公开可访问、许可或公共使用条件清楚、内容包含实验方法或工程记录，并能映射到现有训练知识点。

## 2. 新增来源

| 领域 | 来源 | 类型与许可 | 本地原始文件 | 切片数 |
| --- | --- | --- | --- | ---: |
| 航空轮胎 | Aircraft Tire Tread Fatigue Wear Experiment, Polymers 2021, DOI 10.3390/polym13071143 | 同行评审论文，CC BY 4.0 | `raw_docs/tire_MDPI_Polymers_2021_fatigue_wear.xml` | 30 |
| 航空轮胎 | NASA TP-1569, Tire Wear, Friction and Temperature | NASA 技术报告，公共使用 | `raw_docs/tire_NASA_TP-1569_1980.pdf` | 102 |
| 航空轮胎 | Developments in New Aircraft Tire Tread Materials | NASA 技术报告，美国政府作品 | `raw_docs/tire_NASA_19770011149_1976.pdf` | 39 |
| 航空刹车 | Manufacturing Parameters and Friction of Aircraft C/C Brake Discs, Coatings 2022, DOI 10.3390/coatings12060768 | 同行评审论文，CC BY 4.0 | `raw_docs/brake_MDPI_Coatings_2022_manufacturing_friction.xml` | 51 |
| 航空刹车 | Frictional Heating of C/C Aircraft Brake, Materials 2020, DOI 10.3390/ma13122691 | 同行评审论文，开放获取 | `raw_docs/brake_MDPI_Materials_2020_frictional_heating.xml` | 54 |
| 航空刹车 | Carbon Brake Wear Predictive Maintenance, Aerospace 2025, DOI 10.3390/aerospace12070602 | 同行评审论文，CC BY 4.0 | `raw_docs/brake_MDPI_Aerospace_2025_predictive_wear.xml` | 135 |
| 复合材料 | Comparison of X-ray CT and Ultrasonic C-Scan for CFRP Impact Damage, Applied Composite Materials 2024, DOI 10.1007/s10443-023-10171-3 | 同行评审论文，CC BY 4.0 | `raw_docs/composite_Springer_2024_Cscan_CT_impact.pdf` | 58 |
| 复合材料 | Cranfield C-scan Impact Damage Data, DOI 10.5281/zenodo.4405277 | 开放数据集元数据，CC BY 4.0 | `raw_docs/composite_Zenodo_4405277_metadata.json` | 5 |

每个来源的作者、年份、URL、许可、SHA-256、下载状态和备注以 `source_registry.json` 为准。

## 3. 解析方式

- NASA 和 Springer PDF：使用 `python -m app.rag.pdf_parser` 调用 `pdftotext`，保留 `Page N` 定位。
- MDPI 论文：下载 JATS XML，使用 `python -m app.rag.structured_parser` 保留标题、摘要、章节 ID、图表说明和许可元数据。
- Zenodo：保存官方记录 metadata JSON，结构化解析 DOI、许可、实验说明和文件下载地址。
- 所有 Markdown：使用 `python -m app.rag.pipeline` 按标题、段落、700 字符窗口和 80 字符重叠切片。
- 英文实验术语会映射为中文训练标签，例如 `fatigue wear -> 疲劳磨损`、`wear pin -> 维护决策`、`C-scan -> 无损检测图像判读`。

## 4. 入库结果

- ES 索引：`aviation_material_knowledge`
- 总片段：785 条
- 航空轮胎：223 条
- 航空刹车：312 条
- 复合材料：250 条
- 官方一手资料：420 条
- 开放获取同行评审论文：328 条
- 开放数据集：5 条
- 人工整理资料：32 条
- BGE 状态：关闭；当前以 Elasticsearch BM25 工作，`hybrid` 模式自动显示为 `hybrid-bm25-only`

## 5. 大文件与版权处理

Cranfield 数据集 ZIP 约 391 MB，本仓库不捆绑该二进制文件，只保存元数据与官方下载地址。两份未完整下载的 MDPI PDF 已移出语料目录，正式解析使用体积更小且结构清晰的 JATS XML。未明确开放许可或需要机构订阅的论文只登记候选链接，不下载、不切片、不入库。

## 6. 复核要求

机器解析并不等于专业结论已获专家确认。正式提交前建议按三个方向各抽检不少于 10 个片段，核对实验条件、单位、材料体系、图表上下文和结论边界，并在 `evaluation/expert_review_form.md` 中记录复核结果。
