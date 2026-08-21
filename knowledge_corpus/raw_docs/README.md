# 原始资料目录说明

该目录在本地用于保存公开文献、官方手册、课程资料和经授权的团队实验原始文件。为避免版权、隐私、体积和重复分发风险，原始文件不上传 GitHub。

公开仓库保留以下可复核内容：

- `knowledge_corpus/parsed_docs/`：人工或 MinerU 解析后的结构化文本；
- `knowledge_corpus/chunks/`：供检索使用的知识切片；
- `knowledge_corpus/index_manifest.json`：来源、领域、标题、标签、难度和入库状态；
- 来源登记、授权边界、证据 ID 和引用信息。

需要重建完整私有知识库时，请根据索引清单取得相应公开来源或已授权原始资料，再执行项目提供的 RAG 管线与 Elasticsearch indexer。
