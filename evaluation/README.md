# 测评集使用说明

本目录提供比赛原型的 50 条测评用例、指标定义、自动评测结果和专家复核表。自动评测用于验证可确定性判断的工程指标，专业语义质量仍由领域专家复核。

此外，`guided_inquiry_eval_cases.json` 提供 15 条动态追问专项用例，覆盖三个材料领域、三类学习者画像、精确工况问答、证据闭合和越权提示防护。

`interface_assistant_eval_cases.json` 提供 39 条全局助手用例，覆盖界面导航、学情上下文、缺失上下文、多轮指代、口语噪声、中英混合、三领域专业问答、精确工况和安全边界。JSON/mock 与 Elasticsearch 模式分别输出独立报告，当前均为 39/39 通过。

真实 Qwen 回答质量测试使用独立文件，不覆盖稳定的 mock/规则测评：

- `qwen_quality_eval_cases.json`：代表性真实模型问题集；
- `qwen_quality_results.json`：最近一次完整原始输出；
- `qwen_quality_summary.md`：最近一次量化摘要；
- `qwen_quality_assessment.md`：整体效果判断、修复项和演示建议；
- `qwen_quality_expert_review.md`：人工专家逐题复核表；
- `qwen_quality_runs/`：每次完整真实模型测评的时间戳归档。
- `qwen_interface_assistant_eval_cases.json`：全局助手真实 Qwen 抽样问题集；
- `qwen_interface_assistant_results.json` / `qwen_interface_assistant_summary.md`：全局助手真实 Qwen 原始结果和摘要。

## 文件说明

- `eval_cases.json`：50 条用例，五类各 10 条。
- `eval_metrics.md`：六项核心评价指标及计算口径。
- `automated_results.json`：自动评测生成的机器可读结果。
- `guided_inquiry_results.json`：动态追问专项机器可读结果。
- `guided_inquiry_summary.md`：动态追问专项人类可读结果。
- `eval_results.md`：自动结果摘要与人工复核记录。
- `full_case_execution_results.json`：50 条用例逐条进入诊断与 6 Agent 管线后的机器可读结果。
- `full_case_execution_status.md`：50 条用例完整执行状态表。
- `机器辅助复核与指标计算报告.md`：指标计算、偏差说明与专家复核边界。
- `review_correction_demo.json/.md`：审核驳回、纠偏重生、二次审核固定案例。
- `expert_review_confirmation.json/.md`：50 条核心用例的专家确认结论与正式指标，复核组、日期和电子确认状态已完整归档。
- `expert_review_form.md`：专业内容抽检表。
- `literature_evidence_eval_cases.json`：10 条公开文献实验卡专项检索用例。
- `literature_evidence_results.json`：真实 Elasticsearch 专项回归结果。
- `literature_evidence_summary.md`：公开文献实验卡专项指标摘要。
- `fallback_acceptance_results.json`：JSON/mock 兜底模式完整 API 闭环结果。
- `fallback_acceptance_summary.md`：兜底模式验收摘要。

## 运行自动评测

动态追问专项工程模式：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.guided_inquiry_runner --use-es
```

移除 `--use-es` 可验证 JSON fallback。当前两种模式均为 15/15 通过；工程模式 Elasticsearch 使用率为 100%。

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.runner
```

逐条运行 50 条核心用例并使用真实 Elasticsearch：

```powershell
python -m app.evaluation.full_case_runner --use-es
```

当前结果为 50/50 通过、Agent 完整率 100%、核心知识点代理覆盖率 97.27%、难度规则匹配率 96%、反馈决策准确率 100%，其中 8 条实际完成审核驳回后的纠偏重生。上述代理指标不替代专家签字指标。

运行固定审核驳回—纠偏重生案例：

```powershell
python -m app.evaluation.correction_demo_runner --use-es
```

根据已确认的专家结论生成逐条复核记录：

```powershell
python -m app.evaluation.expert_confirmation_runner
```

该命令还会生成 `expert_review_tasks.md`，其中包含固定抽取的 15 条专家复核任务及逐条评分区。正式复核时应完整执行该清单，不应只挑选系统表现较好的用例。

运行后同时生成：

- `automated_results.json`：50 条核心用例、10 条多维增强用例和逐项机器结果；
- `automated_summary.md`：比赛使用的指标摘要与 15 条分层专家抽检清单。

多维增强用例会检查 `expected_evidence_sources` 是否已登记。当前共核对 15 个来源引用，覆盖率为 100%。该检查证明来源链存在，但不替代专家对片段相关性和专业结论的复核。

自动评测会主动切换到无副作用的 JSON 离线基线，不写入 MySQL、不访问 Elasticsearch、不调用 LLM；结束后恢复进程内原配置。

当前自动覆盖：

1. 50 条数据结构和类别平衡；
2. 10 条检索用例的 Top-3 evidence_id 命中；
3. 航空轮胎、航空刹车片、复合材料板三领域的 6 Agent 完整率；
4. 8 条含明确正确率的反馈决策准确率；
5. 三领域四类资源和审核输出结构完整性。

以下内容必须人工完成：

1. 核心知识点覆盖率；
2. 幻觉率；
3. 资源难度适配准确率；
4. 两条定性反馈用例；
5. 生成内容的专业边界与适航表述检查。

## 团队实验专项测评

- `team_experiment_eval_cases.json`：第一批团队实验多模态证据专项用例20条。
- `team_experiment_eval_cases_batch2.json`：第二批紫外形貌与载荷-距离矩阵专项用例20条。

第二批用例不只检查接口状态，还检查以下比赛验收要点：跨时长形貌比较是否控制图像角色和尺度标签；载荷与距离是否按单变量路径比较；图像结论是否与磨损量、硬度交叉验证；缺失温升是否保持证据不足；ReviewAgent 和 DecisionAgent 是否执行降级与反馈决策。

运行第二批量化测评：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.batch2_runner --quiet
```

该命令关闭 SQL 写入、BGE 和 LLM，但保留当前 Elasticsearch 工程检索，生成：

- `batch2_automated_results.json`：20条逐项机器结果；
- `batch2_evaluation_summary.md`：量化指标和未命中诊断；
- `batch2_expert_review_tasks.md`：20条专家逐项复核任务；
- `batch2_asset_verification_checklist.md`：紫外参数、15单元矩阵和温升映射核对表。

当前自动结果：实验资产检索用例命中率100%，期望资产引用召回率100%，Agent完整率100%，资源结构完整率100%，证据可追溯率100%，反馈决策准确率100%。核心 50 条另经专家复核确认专业正确率100%、幻觉率0%、难度适配准确率100%；第二批实验依据专项仍保留独立人工复核状态，不能用机器结构检查代替。

## 个性化与证据边界测评

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.personalization_review_runner
```

输出文件：

- `personalization_review_results.json`：三类画像差异和5类高风险请求逐项结果；
- `personalization_review_summary.md`：画像策略对照和自动拦截指标摘要。

当前自动结果：4项画像差异指标和2项高风险请求审核指标均为100%。该结果证明规则执行完整，不等同于专业正确率或真实幻觉率。

## 公开文献实验卡专项测评

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.evaluation.literature_evidence_runner
```

10 条用例覆盖 5 张已人工复核实验卡和三个材料方向。当前真实 ES 结果为：来源 Top-5 命中率 100%、evidence_id 可追溯率 100%、人工复核覆盖率 100%、适用边界说明覆盖率 100%、Elasticsearch 使用率 100%。

## JSON / mock 兜底模式验收

```powershell
cd D:\agents
.\scripts\run_fallback_acceptance.ps1
```

该验收临时设置 `DATA_BACKEND=json`、`DATABASE_ENABLED=false`、`ES_ENABLED=false`、`LLM_ENABLED=false`，完整调用画像、题目、诊断、Agent、资源、报告、Markdown 导出和反馈接口。当前结果为：6 个主流程 Agent、4 类个性化资源、4 步反馈迭代全部通过，检索来源为 `local-json`。
