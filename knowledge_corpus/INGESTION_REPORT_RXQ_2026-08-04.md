# 团队老化实验数据入库报告

## 1. 数据集

- 数据集编号：`TIRE-EXP-RXQ-AGING-001`
- 领域：航空轮胎胎面橡胶损伤分析
- 授权状态：`authorized`
- 审核用途：教学训练、系统检索、比赛展示和评审提交
- 安全边界：不构成真实航空轮胎维修或适航放行依据

## 2. 正式化结果

| 对象 | 数量 |
| --- | ---: |
| 样品记录 | 18 |
| 老化工况 | 9 |
| 磨损记录 | 18 |
| 紫外拉伸曲线映射 | 9 |
| SEM/光学代表图 | 14 |
| 图像标注 | 14 |
| 训练案例 | 7 |
| 多维表征类别 | 5 |

多维表征包含摩擦系数、界面温度、质量损失与硬度变化、表面粗糙度、EDS、DMA、定伸应力和印泥法接触压力记录。9 份紫外拉伸 CSV 已通过“拉伸报告机号→样品号”和“试验协议样品号→老化时长”两级证据完成绑定。

## 3. 证据链

1. 原始精选副本位于 `raw_docs/team_tire/pending_review/rxq_aging_experiments/`。
2. 正式实验记录位于 `raw_docs/team_tire/data/tire_rxq_aging_experiment_records.xlsx`。
3. 图像索引位于 `raw_docs/team_tire/data/tire_rxq_damage_image_annotations.xlsx`。
4. 每条磨损记录使用 `RXQ-WEAR-*`，每张图使用 `RXQ-IMG-*`，案例使用 `RXQ-CASE-*`。
5. `source_inventory.json` 保存精选原始文件 SHA-256；正式图像工作簿保存每张图 SHA-256。
6. Markdown 与切片位于 `parsed_docs/` 和 `chunks/`，并登记到 `source_registry.json` 与 `index_manifest.json`。

## 4. 补充确认的试验条件

- 热氧老化：`HD-E701` 通风老化箱，75 °C，空气气氛，依据 `GB/T 3512-2014`。
- 滑动磨损：`CFT-I`，50 N，100 r/min，10000 r，100 min，25±1 °C、45±3% RH；80 目砂轮，2000 目砂纸预处理。
- 紫外老化：`HZ-2008A`，`UVA-340`，295-365 nm，0.6 W/m²。
- 拉伸：`WDT-10`，依据 `GB/T 528`，25 °C，500 mm/min，标距 25 mm。

## 5. 数据限制与来源差异

- 热氧磨损工作簿含 2 d 组，而定稿论文方案未列 2 d；按原始记录保留并标记为来源版本差异。
- 紫外协议、文件夹和拉伸映射使用 504 h，论文表 2.3 记为 507 h；按实际文件采用 504 h，同时保留冲突说明。
- 论文报告接触压力约 0.88 MPa；印泥法辅助工作簿在 50 N 下记录 0.8005 MPa。两者作为不同证据来源并列保存，不强行合并。
- 形貌图为代表视野，不能替代统计采样，也不能单独证明唯一损伤机理。
- 配方、人员和设备资产信息已匿名化，不重建未授权商业信息。

## 6. 入库结果

- 入库前 ES 文档数：1,382
- 入库后 ES 文档数：1,416
- RXQ 数据集可检索切片：34（正式实验记录 20，补充多维证据 14）
- BGE：未启用，当前使用 Elasticsearch BM25；现有 hybrid 配置自动工作在 `hybrid-bm25-only`。
- 检索验证：查询“紫外老化、拉伸性能、UVA-340”时，前两条均命中 `紫外拉伸样品-时长-曲线映射`，知识来源为 Elasticsearch。

## 7. 复现命令

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.import_rxq_aging_dataset
python -m app.rag.team_dataset_validator
python -m app.rag.team_dataset_pipeline --ingest --index
pytest
```
