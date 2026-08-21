# 知识库构建与 RAG 检索方案

## 1. 原始资料来源

当前原型知识库来自公开论文、FAA/NASA/NTSB 技术报告、开放数据集元数据、已授权课题组轮胎资料和人工整理的领域案例。覆盖：

- 航空轮胎胎面橡胶热氧老化、滑动磨损、裂纹剥落和耦合损伤边界；
- 航空刹车片高温摩擦、热衰退、氧化裂纹和失效机理；
- 飞机复合材料板冲击损伤、分层、无损检测和损伤扩展。

当前团队没有航空制动与复合材料实验数据，这两个方向只从公开论文、公开报告和开放数据集提取，不虚构“团队实测”结论。未来若取得新的实验资料，必须先完成授权、脱敏、工况映射和专家复核，再进入正式索引。

## 2. MinerU / Markdown 解析流程

当前系统暂不要求前端上传 PDF。推荐流程：

1. 将 PDF 或扫描资料经 MinerU 解析为 Markdown；
2. 将 Markdown 放入 `knowledge_corpus/parsed_docs/`；
3. 使用 `backend/app/rag/chunker.py` 切片；
4. 使用 `backend/app/rag/pipeline.py` 生成 chunks 并可选导入 ES。

如果无法使用 MinerU，也可以人工整理 Markdown，字段和流程保持一致。

## 3. 文本清洗规则

- 合并多余空白；
- 保留标题层级；
- 删除页眉页脚、重复页码和无意义符号；
- 对表格和图片说明转写为文本描述；
- 对真实人员、单位、设备编号和敏感记录做脱敏。

## 4. 知识切片策略

切片规则：

- 以 Markdown 标题作为主题边界；
- 段落过长时按固定长度切片；
- 使用少量 overlap 保留上下文；
- 每个 chunk 保留来源、领域、标题、标签、难度和适用学习者；
- 通过 `index_manifest.json` 记录每个 evidence_id 的来源与入库状态。

当前知识库由 17 条人工整理基础片段、1,692 条外部资料及领域笔记解析片段和 57 条课题组授权轮胎专题切片构成，共 1,766 条并已写入 ES。外部语料包含 FAA/NASA/NTSB 官方资料、开放获取同行评审论文和开放数据集元数据；2026-08-08 新增橡胶热老化、疲劳裂纹扩展、NASA 高能制动摩擦磨损、复材 BVID 重构和 CFRP 冲击数据集五份一手资料，并提取为 5 张公开文献实验卡。2026-08-09 又从 FAA-H-8083-31B（2023）定向抽取复材 NDI 与航空刹车检查维护章节，新增 81 条官方一手切片。研究论文承担机理与实验现象解释，FAA 维修手册承担检查流程与安全边界约束。10 条文献专项查询和 6 条 FAA 维修专项查询在真实 ES 上的 Top-5 来源命中率与证据可追溯率均为 100%。课题组轮胎资料包含 4 个专题、53 项已审核资产；制动与复材不宣称团队实测。

## 5. BGE embedding 方案

系统预留 BGE embedding 接口：

```env
BGE_ENABLED=false
BGE_MODEL_PATH=
EMBEDDING_BACKEND=none
```

默认不加载模型，不影响演示。如果本地提供 BGE 模型路径，可设置：

```env
BGE_ENABLED=true
BGE_MODEL_PATH=D:\models\bge-small-zh-v1.5
EMBEDDING_BACKEND=bge
```

当前实现会尝试加载 `sentence_transformers`。加载失败时自动跳过向量化，继续使用 BM25。

## 6. Elasticsearch 索引字段

索引名：

```text
aviation_material_knowledge
```

字段：

- `id`
- `domain`
- `title`
- `tags`
- `difficulty`
- `content`
- `source_type`
- `applicable_learners`
- `common_misconceptions`

后续可扩展：

- `source_id`
- `embedding`
- `chunk_version`
- `license`

## 7. BM25 / Vector / Hybrid 检索模式

环境变量：

```env
RETRIEVAL_MODE=hybrid
```

可选值：

- `bm25`：使用 Elasticsearch 关键词检索；
- `vector`：使用 BGE embedding 或开发用 embedding 计算相似度；
- `hybrid`：融合 BM25 和向量检索结果。

第一版在无 BGE 时，`hybrid` 会自动退化为 BM25-only，但仍保留检索模式字段，便于展示后续扩展方向。

为避免长篇论文或报告连续占满前五条证据，BM25 结果增加来源多样性重排：保留原始相关性顺序，在候选来源充足时同一 `source_id` 最多进入两条。检索结果因此可以同时呈现教学基础片段、官方规范、实验论文和事故案例，再由审核 Agent 依据 `source_authority` 与 `source_locator` 交叉核验。

## 8. fallback 机制

系统具有多层 fallback：

1. ES 可用：优先 Elasticsearch BM25；
2. ES 不可用：回退本地 JSON 检索；
3. BGE 不可用：跳过向量化，继续 BM25；
4. LLM 不可用：使用 mock/template 生成。

因此正式演示可以使用 SQL + ES 工程模式，现场异常时仍能切回纯 mock/JSON 模式。

## 9. 当前已入库知识片段统计

- 索引名：`aviation_material_knowledge`
- 当前知识片段：1,766 条
- 航空轮胎：7 条
- 航空刹车片：5 条
- 飞机复合材料板：5 条

## 10. 后续扩展计划

- 将更多公开文献和课程资料通过 MinerU 转为 Markdown；
- 引入 BGE 或其他中文 embedding 模型；
- 将向量写入 ES dense_vector 并使用 kNN；
- 设计 BM25 + vector + rerank 的混合检索；
- 增加知识片段版本管理和引用规范。

## 11. 官方维修证据层

为避免仅凭论文实验结果直接推导维修动作，检索证据按用途分层：

- 机理证据：同行评审论文、NASA 技术报告和团队授权实验资料；
- 操作边界：FAA 维修手册、适航通告和制造商批准资料；
- 训练输出：GenerationAgent 可以组合两类证据，但 ReviewAgent 必须保留 evidence_id 和适用限制；
- 降级原则：若只有机理证据而缺少操作边界，系统只能生成观察、比较和进一步检查建议，不给出放行或维修批准结论。

FAA 维修专项测评位于 `evaluation/maintenance_evidence_eval_cases.json`，结果位于 `evaluation/maintenance_evidence_summary.md`。


