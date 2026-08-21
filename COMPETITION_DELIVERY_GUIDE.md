# 比赛交付材料总说明

## 1. 交付结论

本项目已经具备比赛要求的三类交付物：材料文档、软件模块和测试数据。当前生成的是“提交候选包”；正式提交前仍需人工补充演示视频、报名表、团队身份信息，并确认最终 PPT。

## 2. 材料文档

| 比赛要求 | 当前文件 | 状态 |
| --- | --- | --- |
| 作品设计实现方案 | `submission_materials/01_作品设计实现方案/航空工程材料多智能体训练系统_作品设计实现方案_正式初稿.docx/.pdf` | 已生成，封面信息待人工填写 |
| 作品介绍 | `submission_materials/02_作品简介与创新点/作品简介.md` | 已完成 |
| 创新点与应用价值 | `submission_materials/02_作品简介与创新点/创新点与应用价值.md` | 已完成 |
| 答辩 PPT | `submission_materials/03_答辩PPT材料/` | 已有候选版，需选定并补身份信息 |
| 10 分钟以内演示视频 | `submission_materials/04_演示视频材料/` | 讲稿与彩排清单已完成，MP4 待录制 |
| 视频完整闭环 | `DEMO_SCRIPT.md`、`docs/演示视频讲稿.md` | 已覆盖画像、诊断、Agent、检索、生成、审核、报告、反馈 |

## 3. 软件模块

| 比赛要求 | 当前文件 | 状态 |
| --- | --- | --- |
| 后端源码 | `backend/app/` | 已完成 |
| 前端源码 | `frontend/src/` | 已完成 |
| 可执行程序（如有） | `frontend/dist/` 静态生产构建 | 已提供可部署构建，不宣称桌面安装程序 |
| 部署说明 | `DEPLOYMENT_GUIDE.md`、`deploy/` | 已完成本机、Compose、fallback 三种方式 |
| 单元测试 | `backend/tests/` | 107 项通过 |
| API 测试 | `API_TEST.md` | 已完成 |
| 自动验收 | `outputs/acceptance/acceptance_latest.md` | 已通过 |
| 评委无密钥复现 | `EVALUATOR_QUICKSTART.md`、`scripts/reviewer_verify.ps1` | 已完成，mock 闭环已实测通过 |
| 源码仓库 | 可选 Git 仓库链接 | 当前本地目录尚未初始化 Git；如使用私有仓库需开放评审权限 |

## 4. 测试数据

| 比赛要求 | 当前文件 | 状态 |
| --- | --- | --- |
| 至少一个垂直领域知识库切片 | `knowledge_corpus/chunks/`、`backend/app/data/knowledge_tire.json` | 已覆盖轮胎、刹车、复材三个方向 |
| 来源与入库证据链 | `knowledge_corpus/index_manifest.json`、`source_registry.json`、`parsed_docs/` | 已完成 |
| 不少于两组差异画像 | `backend/app/data/profiles.json` | 共 3 组 |
| 完整输入输出样例 | `submission_materials/06_测试数据与知识库/完整输入输出样例/` | 共 3 组 |
| 多智能体中间数据 | 每个完整样例的 `agent_run.agent_steps` | 每组 6 步 |
| 个性化资源 | 每个完整样例的 `generated_resources` | 讲义、指南、分阶题、案例任务 |
| 学情报告 | 每个完整样例的 `learning_report` | 已包含 |
| 测评集 | `evaluation/eval_cases.json` | 50 条主用例及多个专项用例 |

## 5. 正式提交前人工待办

1. 在设计方案封面和 PPT 中填写学校、团队、申报人、指导教师等信息。
2. 使用 `submission_materials/03_答辩PPT材料/航空工程材料多智能体训练系统_答辩PPT_正式提交版.pptx`，核对最新口径：ES 1,766 条、53 项实验资产、后端 116 passed。
3. 按 `docs/演示视频讲稿.md` 录制小于 10 分钟的 MP4，并检查画面和声音。
4. 填写赛事报名表并按要求签章。
5. 核对所有拟提交的论文、图片、实验资产授权、引用与脱敏状态。
6. 把视频、报名表和最终 PPT 放入 `submission_materials` 后重新生成发布包和 SHA-256。
7. 若提供私有源码仓库，提前添加评审账号或设置赛事要求的访问方式。
8. 撤销任何曾在聊天、截图或邮件中出现过的模型 Key；不要向评委提供个人长期密钥，真实模型复现使用 BYOK 临时密钥。

## 6. 候选包与最终包

候选包用于团队内部检查，可缺少人工材料。正式包必须通过：

```powershell
cd D:\agents
.\scripts\build_release_package.ps1 -Final
```

`-Final` 会检查 MP4、报名表、PPT、设计方案、完整样例和验收报告；缺失时拒绝生成最终包。未使用 `-Final` 时生成明确标记的候选包。

压缩包建议命名：

```text
学校—申报人姓名—面向航空工程材料损伤分析的多智能体个性化知识生成与实操训练系统—联系电话.zip
```

