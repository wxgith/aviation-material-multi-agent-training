# 差异化学习者完整输入输出样例

本目录由 `python -m app.evaluation.submission_examples_runner` 通过当前运行中的后端 API 自动生成。
每个 JSON 均包含学习者画像、诊断提交、诊断结果、6 个 Agent 中间步骤、4 类生成资源和学情报告。

| 学习者 | 领域 | 得分 | Agent 步骤 | 资源形态 | 检索来源 | 文件 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 本科低年级学生 | tire | 60 | 6 | 4 | elasticsearch | `undergrad_basic_tire_complete_example.json` |
| 材料方向研究生 | brake | 80 | 6 | 4 | elasticsearch | `grad_materials_brake_complete_example.json` |
| 机务维修新员工 | composite | 60 | 6 | 4 | elasticsearch | `maintenance_new_composite_complete_example.json` |

> 这些文件是演示和提交测试数据，不代表专业指标已由专家签字确认。
