# 当前验收摘要

> 本文件是比赛提交候选版的当前状态入口。`outputs/acceptance/` 中的旧文件属于历史整套验收快照，不作为当前数字口径。

## 当前冻结口径

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 后端单元与集成测试 | 116 passed | `pytest`；`competition_baseline.json` |
| 前端生产构建 | passed | `npm run build` |
| Elasticsearch 知识切片 | 1,766 | `aviation_material_knowledge`；`competition_baseline.json` |
| 核心确定性测评 | 50/50 | `evaluation/full_case_execution_results.json` |
| 动态追问专项 | 15/15 | `evaluation/guided_inquiry_results.json` |
| 全局助手专项 | JSON 39/39；ES 39/39 | `evaluation/context_assistant_results.json` |
| Qwen 代表性机器检查 | 6/6 | `evaluation/qwen_quality_results.json` |
| 审核门控配对对照 | 3/6 -> 6/6 | `evaluation/review_gate_ablation_report.md` |
| SQL + ES 录屏预检 | passed | `outputs/demo/demo_preflight_latest.json` |

## 复核边界

- 50 条核心用例已有项目团队领域复核记录；若赛事要求独立具名专家签字，须补充真实签字或可核验记录。
- Qwen 结果中的 6/6 是结构、证据、安全和流程机器检查，不等同于外部专家专业正确率。
- 外部专家盲审和真实用户前后测材料已生成，但结果字段保持空白，等待真实采集。
- 本轮没有重新运行耗时较长的完整 `run_acceptance.ps1`；当前结论来自最新分项测试、确定性测评、构建检查和演示预检。

## 提交前人工动作

1. 录制并放入 10 分钟以内的 MP4。
2. 填写报名表、学校、团队、答辩人和指导教师信息。
3. 完成外部专家盲审与真实用户试用，或在答辩中明确列为后续验证。
4. 加入人工材料后使用 `scripts/build_release_package.ps1 -Final` 重新生成最终包。
