# 知识库语料构建说明

本目录记录航空工程材料损伤分析知识库的证据链，用于说明知识片段从原始资料到检索索引的构建过程。

## 目录结构

```text
knowledge_corpus/
├─ raw_docs/        # 原始领域资料说明或占位文件
├─ parsed_docs/     # MinerU 或人工整理后的 Markdown 文本
├─ chunks/          # 切片后的 JSON 文件
├─ index_manifest.json
└─ README.md
```

## 资料来源

具体的检索入口、文件命名、版权处理、MinerU 清洗和证据链字段要求见 [MATERIAL_COLLECTION_GUIDE.md](MATERIAL_COLLECTION_GUIDE.md)。待收集与已收集来源统一登记在 [source_registry.json](source_registry.json)，不要只把 PDF 放进目录而不登记来源。

在线检索、下载、解析与入库明细见 [INGESTION_REPORT_2026-08-03.md](INGESTION_REPORT_2026-08-03.md)、[INGESTION_REPORT_2026-08-04.md](INGESTION_REPORT_2026-08-04.md)、[INGESTION_REPORT_2026-08-08.md](INGESTION_REPORT_2026-08-08.md) 和 [INGESTION_REPORT_2026-08-09.md](INGESTION_REPORT_2026-08-09.md)。

当前原型使用公开课程知识、工程训练说明、实验记录模板和人工整理的领域笔记构建演示语料。正式扩展时，资料应来自：

- 公开教材、课程讲义或已授权教学材料；
- 公开论文、标准摘要或团队内部已授权实验说明；
- 航空轮胎、刹车片、复合材料板损伤分析相关实验规程；
- 经过脱敏处理的训练案例。

## 解析方式

如果资料为 PDF，可先使用 MinerU 解析为 Markdown。当前系统暂不强制接入前端 PDF 上传，后端 RAG 管线优先支持读取 `parsed_docs/` 下的 Markdown 文件。

流程：

1. 原始资料登记在 `raw_docs/`。
2. MinerU 或人工整理后输出 Markdown 到 `parsed_docs/`。
3. `backend/app/rag/chunker.py` 按标题、段落和固定长度切片。
4. `backend/app/rag/embedder.py` 可选生成 BGE embedding；默认关闭。
5. `backend/app/rag/pipeline.py` 可将切片导入 Elasticsearch。

已登记且下载的 PDF 可直接解析：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.pdf_parser
```

解析器调用本机 `pdftotext`，按 `source_registry.json` 中的 `ingest_page_ranges` 选择专业相关页面，并在 Markdown 中保留 `Page N` 定位。MinerU 输出仍可直接放入 `parsed_docs/`，两种方式可以并存。

开放获取论文的 JATS XML 和 Zenodo 数据集元数据可使用结构化解析器：

```powershell
python -m app.rag.structured_parser
```

JATS 解析会保留论文标题、摘要、章节编号、图表说明和许可信息；Zenodo 解析会保留 DOI、许可、实验记录、文件大小与官方下载地址。解析产物统一写入 `parsed_docs/`，并标记为“机器解析，待专家复核”。

## 当前真实语料统计

- 已登记并校验外部公开物理资料：24 份，对应 26 条逻辑来源记录；
- 原始资料格式：PDF、JATS XML、Zenodo JSON metadata；
- 人工整理基础片段：17 条；
- 外部资料及领域笔记解析片段：1,692 条；
- 团队实验专题切片：57 条，对应 4 个专题、53 项已审核实验资产；
- Elasticsearch `aviation_material_knowledge`：1,766 条；
- 带 `source_locator` 的片段：1,766 条；
- 领域分布：航空轮胎 795 条、航空制动 536 条、复合材料 435 条；
- 来源级别：官方一手资料 1,176 条、开放获取同行评审论文 481 条、开放数据论文 15 条、开放数据集 5 条、团队授权实验 57 条、人工整理资料 32 条。

2026-08-08 新增 5 份一手实验资料：天然橡胶/炭黑热老化、填充天然橡胶疲劳裂纹扩展、NASA 碳-石墨高能制动摩擦磨损、复合材料 BVID 超声重构，以及 CFRP 冲击表面/内部损伤配对数据。它们合计新增 246 条切片，具体边界见当日入库报告。

2026-08-09 新增 FAA-H-8083-31B（2023）维修手册章节摘录：复合材料 NDI 物理页 351–355，以及航空刹车构造、检查与维护物理页 773–774、797–803。两条逻辑来源共新增 81 条官方一手切片，用于补齐“论文解释机理、官方手册约束操作边界”的双层证据链。完整 110 MB PDF 不复制进比赛提交包，仅保留官方链接、SHA-256、页码摘录和切片。

上述五份资料还提取为 5 张“公开文献实验卡”，保存在 `literature_evidence/experiment_records.json`。实验卡记录试样、设备、工况、观测指标、结论、证据 ID 和限制说明，并已完成参数转录、来源定位和适用边界人工复核。该复核不代表重复开展原论文试验。当前团队没有制动和复材自有实验数据，系统不会将这些文献结果表述为团队实测。

Cranfield C-scan 数据集压缩包约 391 MB，当前提交包只保存 Zenodo 元数据、许可和下载地址，不捆绑原始二进制数据。需要开展算法实验时再从来源页单独下载。

## 切片规则

- 一级到四级标题作为主题边界；
- 段落清洗后按 `max_chars=700` 切片；
- 长文本使用少量 overlap 保留上下文；
- 每个 chunk 保留来源、领域、标题、标签、难度、内容、适用学习者和常见误区；
- 切片 ID 使用来源名、序号和内容摘要哈希生成，便于追溯。

## 字段结构

```json
{
  "id": "tire-k01",
  "domain": "tire",
  "title": "热氧老化与橡胶交联网络变化",
  "tags": ["热氧老化", "损伤机理"],
  "difficulty": "基础",
  "content": "知识片段正文",
  "source_type": "domain_note",
  "source_id": "parsed_tire_damage_notes",
  "applicable_learners": ["本科低年级学生"],
  "common_misconceptions": ["常见误区"]
}
```

## 入库流程

导入已有 JSON 知识库：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.search.indexer
```

运行 Markdown RAG 管线：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.pipeline
```

正式录屏前无需重复运行该命令。当前工程演示索引已固定为 1,766 条；只有新增或修改资料后才需要重新执行 pipeline。

默认 `BGE_ENABLED=false`，管线会跳过向量化，仅保留 BM25 检索能力。若提供 BGE 模型路径，可开启 embedding 扩展。


