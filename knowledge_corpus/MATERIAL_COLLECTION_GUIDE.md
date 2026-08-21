# 领域资料采集、保存与入库指南

## 1. 先找什么

按“权威标准与手册 → 高质量综述 → 代表性论文 → 团队授权实验资料”的顺序收集。第一批建议每个方向先准备 5 至 10 份可靠资料，不追求数量，优先补齐损伤定义、试验边界、表征方法、常见误区和实操流程。

推荐检索入口：

- 官方手册：FAA、NASA Technical Reports Server、国家标准全文公开系统；
- 标准元数据：ISO、ASTM、全国标准信息公共服务平台；
- 学术文献：Web of Science、Scopus、Engineering Village、Google Scholar、中国知网；
- 团队资料：已授权课程讲义、实验 SOP、去标识化实验记录和自有论文。

建议关键词：

| 方向 | 中文关键词 | 英文关键词 |
| --- | --- | --- |
| 航空轮胎 | 航空轮胎、胎面橡胶、热氧老化、滑动磨损、裂纹、剥落 | aircraft tire, tread rubber, thermo-oxidative ageing, sliding wear, crack, spalling |
| 航空刹车片 | 航空刹车、摩擦材料、热衰退、氧化膜、热裂纹 | aircraft brake, friction material, brake fade, oxide film, thermal crack |
| 复合材料板 | 低速冲击、分层、基体开裂、纤维断裂、超声 C 扫 | low-velocity impact, delamination, matrix cracking, fiber breakage, ultrasonic C-scan |

## 2. 下载后存到哪里

1. 可公开或已获授权的原始 PDF：放入 `knowledge_corpus/raw_docs/`。
2. 受版权保护、无再分发许可的标准：不保存进提交包，只建立 `*_metadata.md`，记录标准号、版本、链接和实际查阅位置。
3. MinerU 或人工整理后的文本：放入 `knowledge_corpus/parsed_docs/`。
4. 程序切片结果：放入 `knowledge_corpus/chunks/`，不要手工直接改 ES 中的数据。
5. 每拿到一份资料，都先登记 `knowledge_corpus/source_registry.json`。

推荐文件名：

```text
tire_FAA_AC20-97B_2005.pdf
tire_ISO188_2023_metadata.md
brake_review_high_temperature_friction_2024.pdf
composite_NASA_NDE_2020.pdf
```

## 3. 来源登记规则

`source_registry.json` 每条来源至少填写：`source_id`、题名、机构或作者、年份、文献类型、标准号、URL、授权状态、本地文件、适用章节、采集状态和备注。下载文件后建议计算 SHA-256：

```powershell
Get-FileHash D:\agents\knowledge_corpus\raw_docs\文件名.pdf -Algorithm SHA256
```

把结果写入该来源的 `checksum`。团队资料还要在 `license_or_authorization` 中注明“团队自有”或授权人、授权日期。

## 4. 解析和清洗

MinerU 输出 Markdown 后放入 `parsed_docs/`，文件开头增加元数据：

```markdown
---
source_id: tire_faa_ac20_97b
title: Aircraft Tire Maintenance and Operational Practices
domain: tire
pages: 1-32
parser: MinerU
review_status: pending
---
```

清洗时保留标题层级、表格标题、图号、页码或章节号；删除页眉页脚、重复目录、无意义换行。不要把 OCR 猜测值当成确定事实。公式、单位、温度和载荷数据必须人工核对。

## 5. 切片与证据链

每个 chunk 至少包含：

```json
{
  "id": "tire-faa-ac20-97b-inspection-001",
  "source_id": "tire_faa_ac20_97b",
  "source_locator": "Section 7 / page 12",
  "domain": "tire",
  "title": "胎面检查要点",
  "tags": ["检查流程", "裂纹", "剥落"],
  "difficulty": "基础",
  "content": "经人工核对的知识内容",
  "review_status": "expert_verified"
}
```

其中 `source_locator` 不能省略。生成内容返回的 `evidence_ids` 对应 chunk ID，chunk 再通过 `source_id + source_locator` 回到原始资料。

## 6. 入库前检查

- 来源是否公开、购买或获得授权；
- 版本号、年份、单位和试验条件是否准确；
- 是否混入真实姓名、学号、联系方式或涉密数据；
- Markdown 是否完成人工核对；
- chunk 是否包含来源定位；
- 专业导师是否完成抽样复核。

通过后运行：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.pipeline
python -m app.search.indexer
```

对于已登记的公开 PDF，可先执行：

```powershell
python -m app.rag.pdf_parser
```

推荐顺序为 `pdf_parser → pipeline`。当前 pipeline 已同时导入原有 JSON 基础片段，因此通常不需要再单独执行 `app.search.indexer`。

最后检查 ES 索引数量，并执行检索测评。正式提交时仅打包公开或明确授权的原文；其他资料保留来源登记和元数据，不随源码分发。

## 7. 当前资料策略

团队目前没有航空制动和复合材料自有实验数据，因此当前版本不把这两类团队数据作为验收前提，也不制作虚构实验记录。两类实验依据从公开论文、NASA/FAA 报告和开放数据集提取，整理到：

```text
knowledge_corpus/literature_evidence/experiment_records.json
```

每条文献实验卡必须包含：

1. `source_id` 和原始来源链接；
2. 材料或试样信息；
3. 设备与可复现实验工况；
4. 观测指标和论文原始结论；
5. 对应的 `evidence_ids` 与章节或页码；
6. 适用边界和 `machine_extracted_pending_expert_review` 状态。

界面和报告必须使用“论文试验显示”“报告记录”或“公开数据集包含”等措辞，不能写成“本系统实测”或“团队试验表明”。航空制动维修限值仍以当前有效的制造商手册和适航文件为准。

现有团队轮胎资料继续保留为已授权实验依据。若未来获得制动或复材团队数据，可使用 `raw_docs/team_brake/pending_review/` 和 `raw_docs/team_composite/pending_review/`，但它们不是当前演示所需资料。

5 张公开文献实验卡已完成领域人工复核，核对范围包括试验单位、试样、工况、趋势结论、证据 ID 和限制说明。后续新增文献仍需按同一流程复核，不能沿用既有卡片的审核结论。
